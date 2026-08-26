"""Leakage-safe feature engineering for Axiom (Razorpay AI Buildathon, Track 2).

The whole "honest metrics" thesis lives or dies here. Every feature that touches
history or the label is computed **as-of**: using only rows that occurred *strictly
before* the current order. Target-encoded features (pincode / buyer RTO rate) are
additionally shrunk toward a **train-only** global prior, so a rare pincode/buyer can
never memorise its own outcome.

Why as-of (expanding) instead of K-fold OOF?
--------------------------------------------
The data is temporal and we split by time. "Use only the past" is both the strictest
anti-leakage rule *and* exactly what a production scorer sees at checkout: at time ``t``
you know every order before ``t`` and none after. So the same code is correct offline
and online.

Guarantees enforced by ``tests/test_features.py``
-------------------------------------------------
* The first time a pincode/buyer is ever seen, its target-encoding equals the prior
  (count = 0) -- i.e. the row's own label is provably unused.
* Prior-count / velocity features are 0 on first sighting.
* No single feature is a near-perfect predictor of the label.
* Train precedes val precedes test in time; the test set is never resampled.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Feature groups (documented so the model + pitch can reference them) -----------------
BASE_NUMERIC = [
    "is_cod", "order_value_log", "order_value_vs_cat_median", "city_tier",
    "distance_km", "address_completeness", "phone_verified", "account_age_days",
    "is_first_time_buyer", "is_serviceable", "order_hour", "order_dayofweek",
]
ENCODED = ["pincode_rto_enc", "buyer_rto_enc", "pincode_orders_prior_log",
           "buyer_orders_prior_log"]
VELOCITY = ["device_orders_24h", "pincode_orders_1h", "buyer_orders_7d"]
GRAPH = ["device_orders_prior_log", "device_distinct_buyers_prior"]
CATEGORICAL = ["product_category"]

FEATURE_COLUMNS = BASE_NUMERIC + ENCODED + VELOCITY + GRAPH + CATEGORICAL


@dataclass
class FeatureBundle:
    """Result of :func:`build_features`."""
    frame: pd.DataFrame                       # orders + engineered features + 'split'
    feature_columns: list[str]
    categorical_columns: list[str]
    label: str = "is_rto"
    meta: dict = field(default_factory=dict)  # train_prior, alpha, split sizes, ...

    def split(self, name: str) -> tuple[pd.DataFrame, pd.Series]:
        """Return (X, y) for 'train' | 'val' | 'test'."""
        sub = self.frame[self.frame["split"] == name]
        return sub[self.feature_columns], sub[self.label]


# --------------------------------------------------------------------------------------
# Leakage-safe primitives (all operate on a time-sorted, RangeIndexed frame)
# --------------------------------------------------------------------------------------

def _assign_time_split(n: int, val_frac: float, test_frac: float) -> np.ndarray:
    """Chronological split labels for ``n`` time-sorted rows (no shuffling)."""
    train_end = int(round(n * (1.0 - val_frac - test_frac)))
    val_end = int(round(n * (1.0 - test_frac)))
    split = np.empty(n, dtype=object)
    split[:train_end] = "train"
    split[train_end:val_end] = "val"
    split[val_end:] = "test"
    return split


def _expanding_target_encode(df: pd.DataFrame, key: str, label: str, prior: float,
                             alpha: float) -> pd.Series:
    """Smoothed mean of ``label`` over rows with the same ``key`` that occurred *earlier*.

    enc = (prior_sum + alpha * prior) / (prior_count + alpha).
    The current row is excluded, so the row's own label never enters its feature.
    """
    grp = df.groupby(key, sort=False)
    prior_count = grp.cumcount().to_numpy()                       # earlier rows for key
    prior_sum = (grp[label].cumsum() - df[label]).to_numpy()      # earlier positives
    return pd.Series((prior_sum + alpha * prior) / (prior_count + alpha), index=df.index)


def _expanding_count(df: pd.DataFrame, key: str) -> pd.Series:
    """Number of earlier rows sharing ``key`` (0 on first sighting)."""
    return df.groupby(key, sort=False).cumcount()


def _velocity_count(df: pd.DataFrame, key: str, window: str) -> pd.Series:
    """Count of earlier rows sharing ``key`` within a trailing time ``window`` (e.g. '24h')."""
    times = df["order_ts"].to_numpy().astype("datetime64[ns]").astype("int64")
    win = np.int64(pd.Timedelta(window).value)
    out = np.zeros(len(df), dtype=np.int64)
    for idx in df.groupby(key, sort=False).indices.values():
        idx = np.sort(idx)                       # ascending time within the group
        t = times[idx]
        left = np.searchsorted(t, t - win, side="left")
        out[idx] = np.arange(len(t)) - left      # earlier rows still inside the window
    return pd.Series(out, index=df.index)


def _device_distinct_buyers_prior(df: pd.DataFrame) -> pd.Series:
    """Distinct buyers seen on this device *before* the current row (fraud-ring fan-out)."""
    is_new_pair = (~df.duplicated(["device_id", "buyer_id"])).astype(int)
    tmp = df.assign(_new=is_new_pair)
    incl = tmp.groupby("device_id", sort=False)["_new"].cumsum().to_numpy()
    return pd.Series(incl - is_new_pair.to_numpy(), index=df.index)


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------

def build_features(orders: pd.DataFrame, val_frac: float = 0.15, test_frac: float = 0.15,
                   alpha: float = 20.0) -> FeatureBundle:
    """Engineer the leakage-safe feature matrix from raw orders.

    Parameters
    ----------
    orders : output of the synthetic COD generator (observable columns + ``is_rto``).
    val_frac, test_frac : chronological validation / test fractions (test keeps its
        natural RTO rate -- it is never resampled).
    alpha : smoothing strength for target encoding (shrinkage toward the train prior).
    """
    df = orders.copy()
    df["order_ts"] = pd.to_datetime(df["order_ts"])
    df = df.sort_values("order_ts", kind="mergesort").reset_index(drop=True)

    df["split"] = _assign_time_split(len(df), val_frac, test_frac)
    train_mask = df["split"] == "train"
    train_prior = float(df.loc[train_mask, "is_rto"].mean())

    # --- base numeric (directly observable at checkout) ------------------------------
    df["order_value_log"] = np.log1p(df["order_value"])
    cat_median = df.loc[train_mask].groupby("product_category")["order_value"].median()
    global_median = float(df.loc[train_mask, "order_value"].median())
    df["order_value_vs_cat_median"] = (
        df["order_value"] / df["product_category"].map(cat_median).fillna(global_median)
    )
    df["order_hour"] = df["order_ts"].dt.hour
    df["order_dayofweek"] = df["order_ts"].dt.dayofweek

    # --- leakage-safe target encoding + prior counts ---------------------------------
    df["pincode_rto_enc"] = _expanding_target_encode(df, "pincode", "is_rto", train_prior, alpha)
    df["buyer_rto_enc"] = _expanding_target_encode(df, "buyer_id", "is_rto", train_prior, alpha)
    df["pincode_orders_prior_log"] = np.log1p(_expanding_count(df, "pincode"))
    df["buyer_orders_prior_log"] = np.log1p(_expanding_count(df, "buyer_id"))

    # --- velocity (bursts) -----------------------------------------------------------
    df["device_orders_24h"] = _velocity_count(df, "device_id", "24h")
    df["pincode_orders_1h"] = _velocity_count(df, "pincode", "1h")
    df["buyer_orders_7d"] = _velocity_count(df, "buyer_id", "7d")

    # --- graph / ring ----------------------------------------------------------------
    df["device_orders_prior_log"] = np.log1p(_expanding_count(df, "device_id"))
    df["device_distinct_buyers_prior"] = _device_distinct_buyers_prior(df)

    # types: LightGBM consumes product_category as a native categorical
    df["product_category"] = df["product_category"].astype("category")

    meta = {
        "train_prior": train_prior,
        "alpha": alpha,
        "n_total": int(len(df)),
        "split_sizes": df["split"].value_counts().to_dict(),
        "test_rto_rate": float(df.loc[df["split"] == "test", "is_rto"].mean()),
    }
    return FeatureBundle(df, FEATURE_COLUMNS, CATEGORICAL, meta=meta)


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Build leakage-safe features for Axiom.")
    ap.add_argument("--in", dest="inp", default="data/cod_orders.csv")
    ap.add_argument("--out", default="data/features.csv")
    ap.add_argument("--alpha", type=float, default=20.0)
    args = ap.parse_args()

    orders = pd.read_csv(args.inp)
    bundle = build_features(orders, alpha=args.alpha)
    df = bundle.frame

    keep = ["order_id", "order_ts", "split", bundle.label] + bundle.feature_columns
    df[keep].to_csv(args.out, index=False)

    m = bundle.meta
    print(f"[axiom] built {len(bundle.feature_columns)} features for {m['n_total']:,} orders "
          f"-> {args.out}")
    print(f"[axiom] split sizes        : {m['split_sizes']}")
    print(f"[axiom] train prior (RTO)  : {m['train_prior']:.4f}")
    print(f"[axiom] test RTO rate      : {m['test_rto_rate']:.4f}  (natural, not resampled)")

    # leakage sanity: first-ever sighting of a pincode must encode to exactly the prior
    first_pin = df.groupby("pincode", sort=False).head(1)
    max_dev = (first_pin["pincode_rto_enc"] - m["train_prior"]).abs().max()
    print(f"[axiom] leakage check      : first-sighting enc == train_prior "
          f"(max deviation {max_dev:.2e})")

    corr = (df[bundle.feature_columns].select_dtypes("number")
            .corrwith(df[bundle.label]).abs().sort_values(ascending=False))
    print("[axiom] top |corr| with label (sanity — none should be ~1.0):")
    for name, val in corr.head(6).items():
        print(f"           {name:<28} {val:.3f}")


if __name__ == "__main__":
    main()
