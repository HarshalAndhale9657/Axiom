"""Tests for the synthetic COD generator.

These lock in the properties the rest of the project depends on: a stable schema,
realistic RTO behaviour, reproducibility, and -- most importantly -- that the hidden
ground-truth drivers never leak into the orders file.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.generate_synthetic_cod import generate

OBSERVABLE = {
    "order_id", "order_ts", "buyer_id", "account_age_days", "is_first_time_buyer",
    "device_id", "phone_verified", "payment_method", "is_cod", "order_value",
    "product_category", "pincode", "city", "city_tier", "is_serviceable",
    "dest_lat", "dest_lon", "distance_km", "address_text", "address_completeness",
    "is_rto",
}
FORBIDDEN = {"pincode_latent_risk", "buyer_latent_propensity", "is_ring", "eta",
             "signup_offset_days"}


@pytest.fixture(scope="module")
def data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return generate(n=4000, seed=0)


def test_schema(data):
    orders, _ = data
    assert set(orders.columns) == OBSERVABLE


def test_no_hidden_columns_leak_into_orders(data):
    """The label's true drivers must not be observable features."""
    orders, _ = data
    assert not any(c.startswith("_") for c in orders.columns)
    assert FORBIDDEN.isdisjoint(orders.columns)


def test_label_is_binary_and_complete(data):
    orders, _ = data
    assert set(orders["is_rto"].unique()) <= {0, 1}
    assert orders.notna().all().all()


def test_realistic_rto_rates(data):
    """COD must be dramatically riskier than prepaid, both in real Indian bands."""
    orders, _ = data
    cod = orders.loc[orders["payment_method"] == "COD", "is_rto"].mean()
    prepaid = orders.loc[orders["payment_method"] == "PREPAID", "is_rto"].mean()
    assert cod > prepaid
    assert 0.18 <= cod <= 0.38, f"COD RTO {cod:.3f} out of band"
    assert 0.01 <= prepaid <= 0.09, f"prepaid RTO {prepaid:.3f} out of band"


def test_tier_gradient(data):
    """Smaller cities (tier 3) should have higher RTO than metros (tier 1)."""
    orders, _ = data
    by_tier = orders.groupby("city_tier")["is_rto"].mean()
    assert by_tier.loc[3] > by_tier.loc[1]


def test_history_and_ring_signals_exist(data):
    orders, _ = data
    repeat_buyers = (orders.groupby("buyer_id").size() > 1).sum()
    shared_devices = (orders.groupby("device_id").size() > 3).sum()
    assert repeat_buyers > 0, "need repeat buyers for buyer-history features"
    assert shared_devices > 0, "need shared devices for fraud-ring features"


def test_value_bounds(data):
    orders, _ = data
    assert orders["order_value"].min() >= 99
    assert orders["order_value"].max() <= 60000


def test_reproducible(data):
    orders, latents = data
    orders2, latents2 = generate(n=4000, seed=0)
    pd.testing.assert_frame_equal(orders, orders2)
    pd.testing.assert_frame_equal(latents, latents2)


def test_different_seed_differs():
    a, _ = generate(n=2000, seed=1)
    b, _ = generate(n=2000, seed=2)
    assert not a["is_rto"].equals(b["is_rto"])


def test_latents_align_with_orders(data):
    orders, latents = data
    assert len(latents) == len(orders)
    assert (latents["order_id"].values == orders["order_id"].values).all()
    assert (latents["is_rto"].values == orders["is_rto"].values).all()
