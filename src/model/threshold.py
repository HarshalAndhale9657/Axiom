r"""Cost-optimal decision thresholds for Axiom — chosen **out-of-sample**.

Why this module exists
----------------------
An earlier version of the evaluation swept the rupee cost curve on the *test* split and
reported the cost at its ``argmin``. That is threshold-selection leakage: the headline
number is then an in-sample **oracle**, unreachable in production, and the "honest
metrics" claim collapses under the first hard question. So:

* **The operating point is fitted on the validation split** (:func:`select_tau_star`),
  exactly like any other hyper-parameter.
* The test split is scored **once**, at that frozen threshold.
* :mod:`src.model.evaluation` additionally reports the test-optimal oracle and the gap
  between the two — the *optimism tax* — so the reader can see what tuning-on-test
  would have bought (and that we did not take it).

Three bands, not one threshold
------------------------------
Axiom does not make a binary flag/no-flag call; it routes each order into GREEN
(approve) / AMBER (step-up friction) / RED (convert-to-prepaid or hold). Each band's
action has its own **cost** and its own **efficacy**, so the two cut-points follow from
decision theory rather than from taste. For an order with calibrated risk ``p``:

===========  ==================================================
band         expected rupee cost
===========  ==================================================
GREEN        ``p * c_FN``
AMBER        ``f_a + p * (1 - e_a) * c_FN``
RED          ``f_r + p * (1 - e_r) * c_FN``
===========  ==================================================

where ``f`` is the friction cost the action imposes (borne on every order it touches,
good or bad — deliberately conservative) and ``e`` is the fraction of would-be returns
it prevents. Setting consecutive pairs equal gives closed-form cut-points::

    tau_low  = f_a / (e_a * c_FN)
    tau_high = (f_r - f_a) / ((e_r - e_a) * c_FN)

Note this is *stricter* than the classic Elkan/BMR break-even
``c_FP / (c_FP + c_FN)``, which assumes friction is free on orders that really would
have returned. We charge it on those too.

Honesty
-------
``e_a`` and ``e_r`` are **assumptions**, not measurements: we have no counterfactual
data on what a step-up would have prevented. They are declared in :class:`ActionModel`,
printed wherever the thresholds are used, and swept in :func:`sensitivity` so the reader
sees how far the cut-points move across the plausible range. Nothing here is tuned to
make a number look good.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.model.evaluation import CostModel, total_cost

THRESHOLDS_FILENAME = "thresholds.json"


@dataclass(frozen=True)
class ActionModel:
    """Cost and efficacy of each band's bounded action.

    ``*_friction_frac`` is expressed as a multiple of the false-positive cost
    ``c_FP(order_value)`` so friction stays example-dependent: annoying a Rs 4,000
    customer costs more than annoying a Rs 400 one.

    Defaults and their justification (all disclosed, all swept in :func:`sensitivity`):

    * ``amber_friction_frac=0.25`` — a step-up is an OTP / address confirmation: cheap,
      a quarter of the cost of a hard challenge.
    * ``amber_efficacy=0.35`` — conservative; most of a step-up's value is deterrence,
      and plenty of genuine-looking returns survive it.
    * ``red_friction_frac=1.00`` — converting COD to prepaid carries the full
      abandonment/servicing cost of a wrongly-challenged good order.
    * ``red_efficacy=0.90`` — a prepaid order barely returns (the generator's own
      COD/prepaid RTO gap, ~27% vs ~4%, implies roughly this).
    """

    amber_friction_frac: float = 0.25
    amber_efficacy: float = 0.35
    red_friction_frac: float = 1.00
    red_efficacy: float = 0.90

    def __post_init__(self) -> None:
        if not 0.0 < self.amber_efficacy < self.red_efficacy <= 1.0:
            raise ValueError("require 0 < amber_efficacy < red_efficacy <= 1")
        if not 0.0 <= self.amber_friction_frac <= self.red_friction_frac:
            raise ValueError("require 0 <= amber_friction_frac <= red_friction_frac")


@dataclass(frozen=True)
class BandThresholds:
    """A frozen, auditable operating point."""

    tau_low: float
    tau_high: float
    tau_star: float          # binary flag/no-flag break-even (the cost-curve headline)
    fitted_on: str           # which split produced these ("val")
    n_fitted: int
    cost_model: dict
    action_model: dict
    note: str = ""

    def band_of(self, p: float) -> str:
        if p < self.tau_low:
            return "green"
        return "red" if p >= self.tau_high else "amber"

    def as_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------------------
# Binary operating point (used by the cost curve / the headline rupee number)
# --------------------------------------------------------------------------------------

def select_tau_star(y: np.ndarray, proba: np.ndarray, order_value: np.ndarray,
                    cm: CostModel | None = None, n_grid: int = 199) -> float:
    """Rupee-cost-minimising binary threshold, fitted on the split it is handed.

    Call this with the **validation** split. Ties resolve to the lower threshold, which
    is the recall-favouring side and therefore the conservative choice for a risk system.
    """
    cm = cm or CostModel()
    y = np.asarray(y, dtype=bool)
    proba = np.asarray(proba, dtype=float)
    order_value = np.asarray(order_value, dtype=float)
    grid = np.linspace(0.005, 0.995, n_grid)
    costs = np.array([total_cost(proba >= t, y, order_value, cm) for t in grid])
    return float(grid[int(np.argmin(costs))])


# --------------------------------------------------------------------------------------
# Three-band cut-points (closed form, from the action economics)
# --------------------------------------------------------------------------------------

def band_cut_points(order_value: np.ndarray, cm: CostModel | None = None,
                    am: ActionModel | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Per-order ``(tau_low, tau_high)`` implied by the action economics.

    Both are clipped to ``[0, 1]``: an action whose incremental cost never pays for its
    incremental efficacy yields a cut-point above 1, i.e. "never take it" — which we
    surface rather than hide.
    """
    cm, am = cm or CostModel(), am or ActionModel()
    value = np.asarray(order_value, dtype=float)
    c_fn, c_fp = cm.c_fn(value), cm.c_fp(value)
    f_a, f_r = am.amber_friction_frac * c_fp, am.red_friction_frac * c_fp

    tau_low = f_a / (am.amber_efficacy * c_fn)
    tau_high = (f_r - f_a) / ((am.red_efficacy - am.amber_efficacy) * c_fn)
    tau_low = np.clip(tau_low, 0.0, 1.0)
    return tau_low, np.clip(np.maximum(tau_high, tau_low), 0.0, 1.0)


def global_band_thresholds(order_value: np.ndarray, cm: CostModel | None = None,
                           am: ActionModel | None = None) -> tuple[float, float]:
    """Portfolio-level cut-points: the per-order formula evaluated at the median order.

    The service applies one global pair (operationally simpler and easier to audit than a
    per-order rule); the median keeps it representative of the book being scored.
    """
    lo, hi = band_cut_points(np.asarray(order_value, dtype=float), cm, am)
    return float(np.median(lo)), float(np.median(hi))


def band_policy_cost(y: np.ndarray, proba: np.ndarray, order_value: np.ndarray,
                     tau_low: float, tau_high: float, cm: CostModel | None = None,
                     am: ActionModel | None = None) -> dict:
    """Expected rupee cost of the full three-band policy under the action model.

    Unlike :func:`~src.model.evaluation.total_cost` (a binary flag), this charges each
    band its own friction and credits it its own efficacy, so competing band settings can
    be compared on money rather than on intuition.
    """
    cm, am = cm or CostModel(), am or ActionModel()
    y = np.asarray(y, dtype=float)
    proba = np.asarray(proba, dtype=float)
    value = np.asarray(order_value, dtype=float)
    c_fn, c_fp = cm.c_fn(value), cm.c_fp(value)

    green = proba < tau_low
    red = proba >= tau_high
    amber = ~green & ~red

    friction = np.where(amber, am.amber_friction_frac * c_fp,
                        np.where(red, am.red_friction_frac * c_fp, 0.0))
    residual = np.where(amber, 1.0 - am.amber_efficacy,
                        np.where(red, 1.0 - am.red_efficacy, 1.0))
    cost = friction + y * residual * c_fn

    n = max(len(y), 1)
    return {
        "cost": float(cost.sum()),
        "cost_per_1k": float(cost.sum() / n * 1000.0),
        "friction_cost": float(friction.sum()),
        "residual_rto_cost": float((y * residual * c_fn).sum()),
        "n_green": int(green.sum()), "n_amber": int(amber.sum()), "n_red": int(red.sum()),
        "green_rto_rate": float(y[green].mean()) if green.any() else float("nan"),
        "amber_rto_rate": float(y[amber].mean()) if amber.any() else float("nan"),
        "red_rto_rate": float(y[red].mean()) if red.any() else float("nan"),
        "tau_low": float(tau_low), "tau_high": float(tau_high),
    }


def sensitivity(order_value: np.ndarray, cm: CostModel | None = None,
                amber_efficacy_grid: tuple[float, ...] = (0.20, 0.35, 0.50),
                red_efficacy_grid: tuple[float, ...] = (0.80, 0.90, 0.95),
                amber_friction_grid: tuple[float, ...] = (0.15, 0.25, 0.40)) -> pd.DataFrame:
    """How far do the cut-points move across the plausible range of our assumptions?

    Printed alongside the headline thresholds so the assumptions are visible rather than
    buried. A conclusion that only survives one corner of this grid is not a conclusion.
    """
    cm = cm or CostModel()
    rows = []
    for e_a in amber_efficacy_grid:
        for e_r in red_efficacy_grid:
            if e_a >= e_r:
                continue
            for f_a in amber_friction_grid:
                am = ActionModel(amber_friction_frac=f_a, amber_efficacy=e_a,
                                 red_efficacy=e_r)
                lo, hi = global_band_thresholds(order_value, cm, am)
                rows.append({"amber_efficacy": e_a, "red_efficacy": e_r,
                             "amber_friction_frac": f_a, "tau_low": lo, "tau_high": hi})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Fit / persist / load
# --------------------------------------------------------------------------------------

def fit_thresholds(y_val: np.ndarray, proba_val: np.ndarray, value_val: np.ndarray,
                   cm: CostModel | None = None, am: ActionModel | None = None,
                   note: str = "") -> BandThresholds:
    """Fit the complete operating point on the **validation** split."""
    cm, am = cm or CostModel(), am or ActionModel()
    tau_low, tau_high = global_band_thresholds(value_val, cm, am)
    return BandThresholds(
        tau_low=tau_low, tau_high=tau_high,
        tau_star=select_tau_star(y_val, proba_val, value_val, cm),
        fitted_on="val", n_fitted=int(len(y_val)),
        cost_model=asdict(cm), action_model=asdict(am),
        note=note or ("Fitted on the validation split only; the test split is scored once "
                      "at these frozen values."),
    )


def save_thresholds(t: BandThresholds, model_dir: str | Path = "models") -> Path:
    path = Path(model_dir) / THRESHOLDS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(t.as_dict(), indent=2), encoding="utf-8")
    return path


def load_thresholds(model_dir: str | Path = "models") -> BandThresholds | None:
    """Load the frozen operating point, or ``None`` if the model was never trained."""
    path = Path(model_dir) / THRESHOLDS_FILENAME
    if not path.exists():
        return None
    return BandThresholds(**json.loads(path.read_text(encoding="utf-8")))
