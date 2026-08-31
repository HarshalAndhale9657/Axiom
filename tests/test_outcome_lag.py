"""Guards for the outcome-availability lag — the second, subtler leak.

An order placed today cannot know whether *yesterday's* order was returned: the delivery
attempt has not resolved yet. These tests pin that discipline down, because it is the kind
of correctness that silently disappears in a refactor and inflates every downstream number.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.generate_synthetic_cod import generate
from src.features.build_features import (
    DEFAULT_OUTCOME_LAG_DAYS,
    _lagged_prior_stats,
    build_features,
)


@pytest.fixture(scope="module")
def orders():
    return generate(n=5000, seed=0)[0]


def _frame(days: list[int], labels: list[int], key: str = "K") -> pd.DataFrame:
    base = pd.Timestamp("2026-01-01")
    return pd.DataFrame({
        "order_ts": [base + pd.Timedelta(days=d) for d in days],
        "k": [key] * len(days),
        "is_rto": labels,
    })


def test_lag_excludes_outcomes_that_have_not_resolved_yet():
    """Hand-checked, orders on days 1/3/8/10 with a 7-day lag.

    Day 1 and day 3 see nothing (nothing has resolved). Day 8 sees only the day-1 order
    (1 + 7 = 8, resolved exactly now). Day 10 sees day 1 and day 3, but *not* day 8 —
    that parcel is still in transit, and a naive as-of encoder would have counted it.
    """
    df = _frame([1, 3, 8, 10], [1, 1, 1, 0])
    count, total = _lagged_prior_stats(df, "k", "is_rto", lag_days=7.0)
    assert list(count) == [0, 0, 1, 2]
    assert list(total) == [0.0, 0.0, 1.0, 2.0]


def test_boundary_order_resolving_exactly_now_is_counted():
    """An outcome that lands exactly at scoring time is knowable — include it, don't round away."""
    df = _frame([0, 7], [1, 0])
    count, total = _lagged_prior_stats(df, "k", "is_rto", lag_days=7.0)
    assert count[1] == 1 and total[1] == 1.0


def test_zero_lag_still_excludes_the_row_itself():
    """Without a lag the encoder must fall back to strictly-earlier, never self-inclusive."""
    df = _frame([0, 1, 2], [1, 1, 1])
    count, total = _lagged_prior_stats(df, "k", "is_rto", lag_days=0.0)
    assert list(count) == [0, 1, 2]
    assert list(total) == [0.0, 1.0, 2.0]


def test_simultaneous_orders_cannot_see_each_other():
    """Two orders at the same instant know nothing about each other."""
    df = _frame([5, 5], [1, 1])
    count, _ = _lagged_prior_stats(df, "k", "is_rto", lag_days=0.0)
    assert list(count) == [0, 0]


def test_groups_are_isolated():
    df = pd.concat([_frame([0, 30], [1, 0], key="A"), _frame([0, 30], [1, 0], key="B")],
                   ignore_index=True)
    count, _ = _lagged_prior_stats(df, "k", "is_rto", lag_days=7.0)
    assert list(count) == [0, 1, 0, 1]


def test_longer_lag_can_only_shrink_visible_history(orders):
    """Monotonicity: raising the lag must never *add* history a row can see."""
    seen = []
    for lag in (0.0, 7.0, 30.0):
        df = build_features(orders, outcome_lag_days=lag).frame
        counts, _ = _lagged_prior_stats(df, "pincode", "is_rto", lag)
        seen.append(counts.sum())
    assert seen[0] >= seen[1] >= seen[2]
    assert seen[0] > seen[2], "a 30-day lag must visibly cost history on this dataset"


def test_first_sighting_still_encodes_to_the_prior_under_lag(orders):
    """The original leakage guard must survive the lag change."""
    bundle = build_features(orders)
    df, prior = bundle.frame, bundle.meta["train_prior"]
    first = df.groupby("pincode", sort=False).head(1)
    assert np.isclose(first["pincode_rto_enc"], prior).all()


def test_lag_is_recorded_in_the_metadata(orders):
    bundle = build_features(orders)
    assert bundle.meta["outcome_lag_days"] == DEFAULT_OUTCOME_LAG_DAYS == 7.0


def test_lagged_encoding_is_never_more_informed_than_unlagged(orders):
    """The lag is a cost we pay, so it must not accidentally *increase* label correlation."""
    lagged = build_features(orders, outcome_lag_days=7.0).frame
    naive = build_features(orders, outcome_lag_days=0.0).frame
    corr = lambda f: abs(np.corrcoef(f["buyer_rto_enc"], f["is_rto"])[0, 1])  # noqa: E731
    assert corr(lagged) <= corr(naive) + 1e-9


def test_velocity_features_are_unaffected_by_the_lag(orders):
    """Velocity counts orders, not outcomes — an order is visible the moment it is placed."""
    a = build_features(orders, outcome_lag_days=0.0).frame
    b = build_features(orders, outcome_lag_days=30.0).frame
    for col in ("device_orders_24h", "pincode_orders_1h", "buyer_orders_7d"):
        pd.testing.assert_series_equal(a[col], b[col])
