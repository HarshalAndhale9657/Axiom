"""SHAP explanations for the Axiom RTO model.

These are the **grounded facts** the LLM reason-code layer is allowed to narrate (and
nothing else) -- which is how we avoid the documented faithfulness-vs-plausibility gap:
the model decides, SHAP says *why*, and the LLM only phrases what SHAP already found.

We explain the underlying LightGBM booster (SHAP on the raw margin). The isotonic
calibrator on top is monotone, so it changes the probability scale but not the *ordering*
or the sign of each feature's contribution -- the explanation stays faithful to the score.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import shap

from src.model.predictor import CalibratedRTOModel

# Plain-English labels so reason codes read naturally (and never expose raw column names).
FEATURE_LABELS: dict[str, str] = {
    "is_cod": "COD payment",
    "order_value_log": "order value",
    "order_value_vs_cat_median": "order value vs. category norm",
    "city_tier": "city tier",
    "distance_km": "buyer–warehouse distance",
    "address_completeness": "address quality",
    "phone_verified": "phone verification",
    "account_age_days": "account age",
    "is_first_time_buyer": "first-time buyer",
    "is_serviceable": "pincode serviceability",
    "order_hour": "order time of day",
    "order_dayofweek": "order day of week",
    "pincode_rto_enc": "delivery pincode's historical RTO rate",
    "buyer_rto_enc": "buyer's historical RTO rate",
    "pincode_orders_prior_log": "pincode order-history depth",
    "buyer_orders_prior_log": "buyer order-history depth",
    "device_orders_24h": "orders from this device in the last 24h",
    "pincode_orders_1h": "orders to this pincode in the last 1h",
    "buyer_orders_7d": "orders by this buyer in the last 7d",
    "device_orders_prior_log": "device order-history depth",
    "device_distinct_buyers_prior": "distinct buyers sharing this device (ring signal)",
    "product_category": "product category",
}


def _to_float(v: object) -> float:
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float("nan")


@dataclass
class Factor:
    """One feature's contribution to a single order's risk score."""
    feature: str
    label: str
    value: float
    shap: float            # signed contribution on the log-odds scale
    direction: str         # "raises" | "lowers"

    def as_dict(self) -> dict:
        return {"feature": self.feature, "label": self.label, "value": self.value,
                "shap": round(self.shap, 4), "direction": self.direction}


@dataclass
class Explanation:
    factors: list[Factor] = field(default_factory=list)

    @property
    def raises(self) -> list[Factor]:
        return [f for f in self.factors if f.direction == "raises"]

    def grounded_reason(self, k: int = 3) -> str:
        """Deterministic, non-LLM reason string (also the fallback when no LLM key)."""
        top = self.raises[:k]
        if not top:
            return "No strong risk drivers; low predicted RTO risk."
        return "Elevated RTO risk driven by " + ", ".join(f.label for f in top) + "."

    def as_payload(self) -> list[dict]:
        return [f.as_dict() for f in self.factors]


class RTOExplainer:
    """Wraps a SHAP TreeExplainer over the model's booster."""

    def __init__(self, model: CalibratedRTOModel) -> None:
        self.model = model
        self.feature_columns = model.feature_columns
        self.explainer = shap.TreeExplainer(model.booster)

    def _shap_matrix(self, X: pd.DataFrame) -> np.ndarray:
        """Return (n_rows, n_features) SHAP contributions for the positive (RTO) class."""
        sv = self.explainer.shap_values(X[self.feature_columns])
        if isinstance(sv, list):                       # [class0, class1]
            sv = sv[1] if len(sv) > 1 else sv[0]
        sv = np.asarray(sv)
        if sv.ndim == 3:                               # (n, features, classes)
            sv = sv[:, :, 1] if sv.shape[2] > 1 else sv[:, :, 0]
        return sv

    def explain_row(self, X_row: pd.DataFrame, top_n: int = 5) -> Explanation:
        """Top-``top_n`` drivers for a single order (a 1-row DataFrame)."""
        sv = self._shap_matrix(X_row)[0]
        order = np.argsort(np.abs(sv))[::-1][:top_n]
        factors = [
            Factor(
                feature=self.feature_columns[i],
                label=FEATURE_LABELS.get(self.feature_columns[i], self.feature_columns[i]),
                value=_to_float(X_row.iloc[0][self.feature_columns[i]]),
                shap=float(sv[i]),
                direction="raises" if sv[i] > 0 else "lowers",
            )
            for i in order
        ]
        return Explanation(factors)

    def global_importance(self, X: pd.DataFrame) -> pd.Series:
        """Mean |SHAP| per feature -- the honest global importance for the pitch."""
        sv = self._shap_matrix(X)
        return pd.Series(np.abs(sv).mean(axis=0), index=self.feature_columns) \
            .sort_values(ascending=False)
