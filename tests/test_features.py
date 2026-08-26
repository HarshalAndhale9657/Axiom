"""Tests for the leakage-safe feature pipeline.

The headline tests are the *leakage guards*: they prove that history/target features
cannot see their own label and use only past information.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.generate_synthetic_cod import generate
from src.features.build_features import FEATURE_COLUMNS, build_features


@pytest.fixture(scope="module")
def bundle():
    orders, _ = generate(n=5000, seed=0)
    return build_features(orders, val_frac=0.15, test_frac=0.15, alpha=20.0)


def test_all_features_present_and_complete(bundle):
    df = bundle.frame
    assert set(FEATURE_COLUMNS).issubset(df.columns)
    assert df[bundle.feature_columns].notna().all().all(), "features must have no NaNs"


def test_first_sighting_target_encoding_equals_prior(bundle):
    """PROOF of no self-leakage: the first time an entity is seen, its target encoding
    equals the (train-only) prior exactly -- the row's own label cannot have been used."""
    df = bundle.frame
    prior = bundle.meta["train_prior"]
    for key, col in [("pincode", "pincode_rto_enc"), ("buyer_id", "buyer_rto_enc")]:
        first = df.groupby(key, sort=False).head(1)
        assert np.allclose(first[col], prior, atol=1e-9), f"{col} leaks on first sighting"


def test_first_sighting_counts_are_zero(bundle):
    df = bundle.frame
    first_pin = df.groupby("pincode", sort=False).head(1)
    first_buyer = df.groupby("buyer_id", sort=False).head(1)
    assert (first_pin["pincode_orders_prior_log"] == 0).all()
    assert (first_buyer["buyer_orders_prior_log"] == 0).all()


def test_velocity_and_graph_are_nonnegative_and_zero_on_first(bundle):
    df = bundle.frame
    for col in ["device_orders_24h", "pincode_orders_1h", "buyer_orders_7d",
                "device_distinct_buyers_prior"]:
        assert (df[col] >= 0).all()
    first_dev = df.groupby("device_id", sort=False).head(1)
    assert (first_dev["device_orders_prior_log"] == 0).all()
    assert (first_dev["device_distinct_buyers_prior"] == 0).all()


def test_no_single_feature_is_a_near_perfect_predictor(bundle):
    """A |corr| ~ 1.0 with the label is the classic fingerprint of leakage."""
    df = bundle.frame
    corr = df[bundle.feature_columns].select_dtypes("number").corrwith(df[bundle.label]).abs()
    assert corr.max() < 0.95, f"suspiciously high corr: {corr.idxmax()}={corr.max():.3f}"


def test_splits_are_chronological_and_test_not_resampled(bundle):
    df = bundle.frame
    train_max = df.loc[df.split == "train", "order_ts"].max()
    val_min = df.loc[df.split == "val", "order_ts"].min()
    val_max = df.loc[df.split == "val", "order_ts"].max()
    test_min = df.loc[df.split == "test", "order_ts"].min()
    assert train_max <= val_min and val_max <= test_min, "splits must not overlap in time"
    # test set keeps a natural (non-trivial, non-resampled) RTO rate
    assert 0.02 < df.loc[df.split == "test", "is_rto"].mean() < 0.60


def test_ring_devices_accumulate_distinct_buyers(bundle):
    """Fraud-ring devices should show high distinct-buyer fan-out (a real signal)."""
    df = bundle.frame
    ring = df[df["device_id"].astype(str).str.startswith("DEV_RING")]
    if len(ring):  # rings exist by construction
        assert ring["device_distinct_buyers_prior"].max() >= 2


def test_reproducible(bundle):
    orders, _ = generate(n=5000, seed=0)
    again = build_features(orders, val_frac=0.15, test_frac=0.15, alpha=20.0)
    pd.testing.assert_frame_equal(
        bundle.frame[bundle.feature_columns].reset_index(drop=True),
        again.frame[again.feature_columns].reset_index(drop=True),
    )
