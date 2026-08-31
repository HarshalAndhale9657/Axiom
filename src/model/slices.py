"""Who does Axiom get wrong, and what does that cost *them*?

Track 2 is graded on "false-positive cost". A single portfolio-wide FP number hides the
part that matters: false positives are not spread evenly across customers. A model can
look excellent overall while systematically taxing tier-3 buyers, or first-time buyers,
or one product category — and those are real people getting friction they did not earn.

So this module cuts the held-out test split into operational slices and reports, per
slice: how many good customers were challenged, what fraction of the good customers in
that slice that is (the **false-positive rate borne by the innocent**), what it cost them
in rupees, and what the misses cost the merchant. The worst rows are meant to be read out
loud, not buried.

Nothing here is a fairness audit in the legal sense: the model uses no protected
attribute, and city tier / category / order value are commercial, not demographic,
variables. It is an operational harm audit — the honest answer to "who pays for your
false positives".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.model.evaluation import CostModel

# Slice definitions: column -> how to bucket it. Each must be computable at checkout.
VALUE_BINS = [0, 500, 1000, 2000, 5000, np.inf]
VALUE_LABELS = ["<₹500", "₹500–1k", "₹1k–2k", "₹2k–5k", "≥₹5k"]


def slice_frame(test: pd.DataFrame) -> pd.DataFrame:
    """Add the human-readable slice columns used by :func:`slice_report`."""
    out = pd.DataFrame(index=test.index)
    out["payment"] = np.where(test["is_cod"].astype(bool), "COD", "prepaid")
    out["city_tier"] = "tier " + test["city_tier"].astype(int).astype(str)
    out["category"] = test["product_category"].astype(str)
    out["order_value"] = pd.cut(test["order_value"], VALUE_BINS, labels=VALUE_LABELS,
                                right=False)
    out["buyer"] = np.where(test["is_first_time_buyer"].astype(bool),
                            "first-time", "returning")
    out["address"] = np.where(test["address_completeness"] >= 0.7,
                              "complete address", "incomplete address")
    return out


def slice_report(test: pd.DataFrame, proba: np.ndarray, tau: float,
                 cm: CostModel | None = None, min_n: int = 40) -> pd.DataFrame:
    """Per-slice error counts and the rupee cost of each error type.

    Parameters
    ----------
    tau : the frozen operating threshold (fitted on validation — never re-tuned here).
    min_n : slices smaller than this are dropped; a 12-order bucket produces a headline
        false-positive rate that is pure sampling noise, and reporting it would be the
        same cherry-picking we are trying to avoid.
    """
    cm = cm or CostModel()
    y = test["is_rto"].to_numpy().astype(bool)
    value = test["order_value"].to_numpy(dtype=float)
    flag = np.asarray(proba, dtype=float) >= tau
    c_fp, c_fn = cm.c_fp(value), cm.c_fn(value)
    slices = slice_frame(test)

    rows = []
    for dimension in slices.columns:
        for level, mask in slices.groupby(dimension, observed=True).groups.items():
            m = slices.index.isin(mask)
            n = int(m.sum())
            if n < min_n:
                continue
            good, bad = m & ~y, m & y
            fp, fn, tp = m & ~y & flag, m & y & ~flag, m & y & flag
            n_good = int(good.sum())
            rows.append({
                "dimension": dimension,
                "slice": str(level),
                "n": n,
                "rto_rate": float(y[m].mean()),
                "flag_rate": float(flag[m].mean()),
                "n_good": n_good,
                "false_positives": int(fp.sum()),
                # The number that matters to a wrongly-challenged customer: of the good
                # customers in this slice, what share did we put through friction?
                "fp_rate_on_good": float(fp.sum() / n_good) if n_good else float("nan"),
                "recall": float(tp.sum() / bad.sum()) if bad.any() else float("nan"),
                "precision": (float(tp.sum() / (tp.sum() + fp.sum()))
                              if (tp.sum() + fp.sum()) else float("nan")),
                "fp_cost": float(c_fp[fp].sum()),
                "fn_cost": float(c_fn[fn].sum()),
                "fp_cost_per_1k_orders": float(c_fp[fp].sum() / n * 1000.0),
                "total_cost_per_1k_orders": float((c_fp[fp].sum() + c_fn[fn].sum()) / n * 1000.0),
            })
    return pd.DataFrame(rows).sort_values(["dimension", "fp_rate_on_good"],
                                          ascending=[True, False]).reset_index(drop=True)


def worst_slices(report: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """The k slices where good customers absorb the most friction — the honest headline."""
    return report.nlargest(k, "fp_rate_on_good")[
        ["dimension", "slice", "n", "n_good", "false_positives", "fp_rate_on_good",
         "fp_cost", "recall"]].reset_index(drop=True)


def disparity(report: pd.DataFrame) -> pd.DataFrame:
    """Spread of the false-positive burden within each dimension (max / min ratio).

    A ratio near 1 means friction lands evenly; a large ratio names a group paying for
    everyone else's fraud. Reported per dimension so the reader sees where the model is
    least even-handed, not just that it is.

    When the least-challenged slice has *no* false positives at all the ratio is
    undefined, not infinite: ``ratio`` is ``None`` and ``unbounded`` is ``True``. Encoding
    that honestly matters — an ``inf`` is not valid JSON, and rendering it as a number
    would invent a comparison the data does not support.
    """
    rows = []
    for dimension, grp in report.groupby("dimension"):
        if len(grp) < 2:
            continue
        worst = grp.loc[grp["fp_rate_on_good"].idxmax()]
        best = grp.loc[grp["fp_rate_on_good"].idxmin()]
        unbounded = not best["fp_rate_on_good"] > 0
        rows.append({
            "dimension": dimension,
            "worst_slice": worst["slice"], "worst_fp_rate_on_good": worst["fp_rate_on_good"],
            "best_slice": best["slice"], "best_fp_rate_on_good": best["fp_rate_on_good"],
            "ratio": (None if unbounded
                      else float(worst["fp_rate_on_good"] / best["fp_rate_on_good"])),
            "unbounded": unbounded,
        })
    # Unbounded dimensions are the most uneven of all, so they sort first.
    return (pd.DataFrame(rows)
            .sort_values(["unbounded", "ratio"], ascending=[False, False], na_position="first")
            .reset_index(drop=True))


def main() -> None:
    import argparse

    from src.features.build_features import build_features
    from src.model.threshold import fit_thresholds, load_thresholds
    from src.model.train import load
    from src.util import enable_utf8_stdout

    enable_utf8_stdout()
    ap = argparse.ArgumentParser(description="Failure-mode matrix: who pays for the FPs?")
    ap.add_argument("--in", dest="inp", default="data/cod_orders.csv")
    ap.add_argument("--model-dir", default="models")
    args = ap.parse_args()

    model = load(args.model_dir)["model"]
    bundle = build_features(pd.read_csv(args.inp))
    val, test = (bundle.frame[bundle.frame["split"] == s] for s in ("val", "test"))
    thresholds = load_thresholds(args.model_dir) or fit_thresholds(
        val["is_rto"].to_numpy(), model.predict_proba(val[bundle.feature_columns]),
        val["order_value"].to_numpy())
    proba = model.predict_proba(test[bundle.feature_columns])

    rep = slice_report(test, proba, thresholds.tau_star)
    print("=" * 104)
    print(f"AXIOM — failure-mode matrix (test split, frozen τ = {thresholds.tau_star:.3f})")
    print("=" * 104)
    cols = ["dimension", "slice", "n", "rto_rate", "recall", "precision",
            "fp_rate_on_good", "fp_cost", "fn_cost"]
    print(rep[cols].to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    print("-" * 104)
    print("WORST — good customers most likely to be challenged:")
    print(worst_slices(rep).to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    print("-" * 104)
    print("Unevenness of the false-positive burden, per dimension:")
    print(disparity(rep).to_string(index=False, float_format=lambda v: f"{v:,.2f}"))


if __name__ == "__main__":
    main()
