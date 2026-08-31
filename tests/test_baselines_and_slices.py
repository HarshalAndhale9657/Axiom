"""Tests for the two exhibits a sceptical reviewer asks for first:

* the ablation ladder — did the ML earn its place, and is the gap bigger than the noise?
* the failure-mode matrix — which good customers pay for the false positives?
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.generate_synthetic_cod import generate
from src.features.build_features import build_features
from src.model.baselines import compare, rules_only_raw
from src.model.evaluation import CostModel, bootstrap_ci
from src.model.slices import disparity, slice_frame, slice_report, worst_slices
from src.model.train import train_model


@pytest.fixture(scope="module")
def fitted():
    orders, _ = generate(n=8000, seed=0)
    bundle = build_features(orders)
    result = train_model(bundle, params={"n_estimators": 200, "learning_rate": 0.05})
    test = bundle.frame[bundle.frame["split"] == "test"]
    proba = result.model.predict_proba(test[bundle.feature_columns])
    return bundle, result.model, test, proba


# --- baselines ------------------------------------------------------------------------

def test_rules_scorecard_never_touches_the_label(fitted):
    """The expert scorecard is hand-written: it must score identically with labels shuffled."""
    bundle, _, test, _ = fitted
    X = test[bundle.feature_columns]
    before = rules_only_raw(X)
    shuffled = test.copy()
    shuffled["is_rto"] = shuffled["is_rto"].sample(frac=1.0, random_state=1).to_numpy()
    after = rules_only_raw(shuffled[bundle.feature_columns])
    np.testing.assert_allclose(before, after)


def test_rules_scorecard_ranks_better_than_chance(fitted):
    """A domain scorecard should be a real opponent, otherwise the ablation is a straw man."""
    bundle, model, test, _ = fitted
    table = compare(bundle, model, n_boot=0)
    rules = table.loc[table["model"] == "rules-only scorecard"].iloc[0]
    assert rules["roc_auc"] > 0.6


def test_every_contender_is_scored_on_identical_terms(fitted):
    bundle, model, _, _ = fitted
    table = compare(bundle, model, n_boot=0)
    assert set(table["model"]) == {"prevalence (no skill)", "rules-only scorecard",
                                   "logistic regression", "LightGBM (Axiom)"}
    # every threshold is fitted on validation, and none defaults to the naive 0.5
    assert (table["tau_val_fitted"] < 0.5).all()
    assert table["cost_per_1k"].notna().all()


def test_champion_beats_the_no_skill_floor(fitted):
    bundle, model, _, _ = fitted
    table = compare(bundle, model, n_boot=0).set_index("model")
    assert (table.loc["LightGBM (Axiom)", "cost_per_1k"]
            < table.loc["prevalence (no skill)", "cost_per_1k"])


def test_paired_gap_intervals_are_reported_and_ordered(fitted):
    """We must publish the interval on the gap, whichever way it falls."""
    bundle, model, _, _ = fitted
    table = compare(bundle, model, n_boot=60)
    row = table.loc[table["model"] == "rules-only scorecard"].iloc[0]
    assert row["champion_gain_pr_auc_lo"] <= row["champion_gain_pr_auc_hi"]
    assert isinstance(bool(row["champion_beats_pr_auc"]), bool)


# --- confidence intervals ---------------------------------------------------------------

def test_bootstrap_interval_brackets_the_point_estimate(fitted):
    from sklearn.metrics import average_precision_score

    bundle, _, test, proba = fitted
    y = test["is_rto"].to_numpy()
    ci = bootstrap_ci(y, proba, test["order_value"].to_numpy(),
                      test["is_cod"].to_numpy(), tau=0.3, n_boot=120)
    point = average_precision_score(y, proba)
    assert ci["pr_auc"]["lo"] <= point <= ci["pr_auc"]["hi"]
    assert ci["pr_auc"]["lo"] < ci["pr_auc"]["hi"]      # a real interval, not a point


def test_bootstrap_is_deterministic_under_a_fixed_seed(fitted):
    bundle, _, test, proba = fitted
    args = (test["is_rto"].to_numpy(), proba, test["order_value"].to_numpy(),
            test["is_cod"].to_numpy())
    a = bootstrap_ci(*args, tau=0.3, n_boot=80, seed=7)
    b = bootstrap_ci(*args, tau=0.3, n_boot=80, seed=7)
    assert a == b


# --- slices ---------------------------------------------------------------------------

def test_slice_frame_uses_only_checkout_observable_fields(fitted):
    _, _, test, _ = fitted
    frame = slice_frame(test)
    assert set(frame.columns) == {"payment", "city_tier", "category", "order_value",
                                  "buyer", "address"}
    assert not frame.isna().all().any()


def test_slice_report_counts_reconcile_with_the_portfolio(fitted):
    bundle, _, test, proba = fitted
    rep = slice_report(test, proba, tau=0.3, min_n=1)
    payment = rep[rep["dimension"] == "payment"]
    assert payment["n"].sum() == len(test)
    assert (rep["false_positives"] <= rep["n_good"]).all()
    assert ((rep["fp_rate_on_good"] >= 0) & (rep["fp_rate_on_good"] <= 1)).all()


def test_tiny_slices_are_dropped_rather_than_reported_as_noise(fitted):
    _, _, test, proba = fitted
    rep = slice_report(test, proba, tau=0.3, min_n=200)
    assert (rep["n"] >= 200).all()


def test_prepaid_absorbs_less_friction_than_cod(fitted):
    """A sanity check on the harm audit: COD is where the model applies its friction."""
    _, _, test, proba = fitted
    rep = slice_report(test, proba, tau=0.3, min_n=1).set_index("slice")
    assert rep.loc["prepaid", "fp_rate_on_good"] < rep.loc["COD", "fp_rate_on_good"]


def test_worst_slices_are_the_actual_worst(fitted):
    _, _, test, proba = fitted
    rep = slice_report(test, proba, tau=0.3)
    worst = worst_slices(rep, k=3)
    assert len(worst) == 3
    assert worst["fp_rate_on_good"].iloc[0] == rep["fp_rate_on_good"].max()
    assert worst["fp_rate_on_good"].is_monotonic_decreasing


def test_disparity_ratio_is_at_least_one(fitted):
    """A max/min ratio below 1 would mean the table is mislabelled."""
    _, _, test, proba = fitted
    rep = slice_report(test, proba, tau=0.3)
    disp = disparity(rep)
    assert not disp.empty
    defined = disp[disp["ratio"].notna()]
    assert (defined["ratio"] >= 1.0).all()
    assert defined["ratio"].is_monotonic_decreasing
    assert (disp["worst_fp_rate_on_good"] >= disp["best_fp_rate_on_good"]).all()


def test_an_undefined_disparity_is_flagged_not_infinite(fitted):
    """inf is not valid JSON and would 500 the API; it must surface as an explicit flag."""
    _, _, test, proba = fitted
    disp = disparity(slice_report(test, proba, tau=0.95, min_n=1))   # so strict nothing flags
    assert not disp.empty
    assert disp["unbounded"].all()
    assert disp["ratio"].isna().all()


def test_a_stricter_threshold_never_creates_false_positives(fitted):
    """Monotonicity guard on the harm audit itself."""
    _, _, test, proba = fitted
    loose = slice_report(test, proba, tau=0.2, min_n=1).set_index(["dimension", "slice"])
    strict = slice_report(test, proba, tau=0.6, min_n=1).set_index(["dimension", "slice"])
    joined = loose.join(strict, rsuffix="_strict")
    assert (joined["false_positives_strict"] <= joined["false_positives"]).all()
