"""Tests for the frozen, out-of-sample operating point.

These guard the single most attackable claim in the project: that the threshold we quote
was not chosen on the data we report it on.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.model.evaluation import CostModel, report
from src.model.threshold import (
    ActionModel,
    BandThresholds,
    band_cut_points,
    band_policy_cost,
    fit_thresholds,
    global_band_thresholds,
    load_thresholds,
    save_thresholds,
    select_tau_star,
    sensitivity,
)


def _toy(n: int = 4000, seed: int = 0):
    rng = np.random.default_rng(seed)
    proba = rng.beta(2, 6, n)
    y = (rng.random(n) < proba).astype(int)          # calibrated by construction
    value = rng.lognormal(6.6, 0.5, n)
    is_cod = rng.random(n) < 0.6
    return y, proba, value, is_cod


def test_tau_star_is_below_the_naive_half():
    """Asymmetric costs (a miss hurts more than friction) must pull the threshold down."""
    y, proba, value, _ = _toy()
    assert select_tau_star(y, proba, value) < 0.5


def test_band_cut_points_are_ordered_and_bounded():
    value = np.array([200.0, 800.0, 5000.0])
    lo, hi = band_cut_points(value)
    assert np.all((lo >= 0) & (lo <= 1)) and np.all((hi >= 0) & (hi <= 1))
    assert np.all(hi >= lo)


def test_cheaper_friction_widens_the_amber_band():
    """A cheaper step-up should catch more orders, not fewer — the formula must be monotone."""
    value = np.full(500, 800.0)
    cheap, _ = global_band_thresholds(value, am=ActionModel(amber_friction_frac=0.10))
    dear, _ = global_band_thresholds(value, am=ActionModel(amber_friction_frac=0.40))
    assert cheap < dear


def test_more_effective_step_up_lowers_its_cut_point():
    value = np.full(500, 800.0)
    weak, _ = global_band_thresholds(value, am=ActionModel(amber_efficacy=0.20))
    strong, _ = global_band_thresholds(value, am=ActionModel(amber_efficacy=0.50))
    assert strong < weak


def test_action_model_rejects_incoherent_assumptions():
    with pytest.raises(ValueError):
        ActionModel(amber_efficacy=0.9, red_efficacy=0.5)      # amber better than red
    with pytest.raises(ValueError):
        ActionModel(amber_friction_frac=1.5, red_friction_frac=1.0)


def test_derived_bands_beat_the_old_hardcoded_ones_on_money():
    """The whole reason for deriving cut-points: they must cost less than the magic numbers."""
    y, proba, value, _ = _toy()
    lo, hi = global_band_thresholds(value)
    derived = band_policy_cost(y, proba, value, lo, hi)
    hardcoded = band_policy_cost(y, proba, value, 0.15, 0.45)
    assert derived["cost"] <= hardcoded["cost"]


def test_band_policy_cost_accounts_reconcile():
    y, proba, value, _ = _toy()
    lo, hi = global_band_thresholds(value)
    r = band_policy_cost(y, proba, value, lo, hi)
    assert r["n_green"] + r["n_amber"] + r["n_red"] == len(y)
    assert r["cost"] == pytest.approx(r["friction_cost"] + r["residual_rto_cost"])


def test_riskier_bands_hold_riskier_orders():
    """Sanity: banding a calibrated score must sort risk monotonically."""
    y, proba, value, _ = _toy()
    lo, hi = global_band_thresholds(value)
    r = band_policy_cost(y, proba, value, lo, hi)
    assert r["green_rto_rate"] < r["amber_rto_rate"] < r["red_rto_rate"]


def test_sensitivity_grid_is_populated_and_ordered():
    value = np.full(200, 800.0)
    grid = sensitivity(value)
    assert not grid.empty
    assert (grid["tau_high"] >= grid["tau_low"]).all()
    assert (grid["amber_efficacy"] < grid["red_efficacy"]).all()


def test_thresholds_round_trip_through_disk(tmp_path):
    y, proba, value, _ = _toy()
    fitted = fit_thresholds(y, proba, value)
    save_thresholds(fitted, tmp_path)
    loaded = load_thresholds(tmp_path)
    assert isinstance(loaded, BandThresholds)
    assert loaded.as_dict() == fitted.as_dict()
    assert loaded.fitted_on == "val"


def test_load_thresholds_is_none_when_absent(tmp_path):
    assert load_thresholds(tmp_path) is None


def test_band_of_covers_the_whole_probability_range():
    y, proba, value, _ = _toy()
    t = fit_thresholds(y, proba, value)
    assert t.band_of(0.0) == "green"
    assert t.band_of(1.0) == "red"
    assert t.band_of((t.tau_low + t.tau_high) / 2) == "amber"


def test_frozen_threshold_never_beats_the_test_oracle():
    """The optimism gap must be non-negative — if it were not, the oracle is miscomputed."""
    y, proba, value, is_cod = _toy()
    rep = report(y, proba, value, is_cod, CostModel(), tau=0.4)
    assert rep["tau_source"] == "val_frozen"
    assert rep["optimism"]["cost_gap"] >= 0.0
    assert rep["at_tau_star"]["cost"] >= rep["oracle"]["cost"]


def test_report_without_tau_is_labelled_as_an_oracle():
    """Falling back to the test-optimal threshold must self-identify, never pass as honest."""
    y, proba, value, is_cod = _toy()
    rep = report(y, proba, value, is_cod)
    assert rep["tau_source"] == "test_oracle"
    assert rep["optimism"]["cost_gap"] == pytest.approx(0.0)
