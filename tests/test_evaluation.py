"""Tests for the cost-based evaluation — the Track-2 grade logic.

Includes a hand-checked cost example and the key economic guarantees: the cost-optimal
threshold sits below the naive 0.5, and the model beats the naive 'block-all-COD' policy.
"""
from __future__ import annotations

import numpy as np

from src.data.generate_synthetic_cod import generate
from src.features.build_features import build_features
from src.model.evaluation import (CostModel, cost_curve, example_dependent_bmr,
                                   precision_at_k, report, total_cost)
from src.model.train import train_model


def test_total_cost_hand_checked():
    """flag=[1,0,1], y=[0,1,1], value=100, c_fp=40, c_fn=200 -> FP(40)+FN(200)=240."""
    cm = CostModel(fn_fixed=200, fn_value_frac=0, fp_fixed=40, fp_value_frac=0)
    flag = np.array([1, 0, 1])
    y = np.array([0, 1, 1])
    value = np.array([100, 100, 100])
    assert total_cost(flag, y, value, cm) == 240.0


def test_example_dependent_costs_scale_with_value():
    cm = CostModel()
    assert cm.c_fn(np.array([3000]))[0] > cm.c_fn(np.array([300]))[0]
    assert cm.c_fp(np.array([3000]))[0] > cm.c_fp(np.array([300]))[0]


def test_precision_at_k_bounds():
    y = np.array([0, 1, 0, 1, 1, 0, 0, 1, 0, 1])
    proba = np.linspace(0, 1, 10)
    p = precision_at_k(y, proba, 0.2)
    assert 0.0 <= p <= 1.0


def _fitted():
    orders, _ = generate(n=8000, seed=0)
    bundle = build_features(orders)
    result = train_model(bundle, params={"n_estimators": 200, "learning_rate": 0.05})
    test = bundle.frame[bundle.frame["split"] == "test"]
    proba = result.model.predict_proba(test[bundle.feature_columns])
    return test, proba


def test_tau_star_below_naive_half():
    """The cost-optimal threshold for an asymmetric-cost problem must be < 0.5."""
    test, proba = _fitted()
    rep = report(test["is_rto"].to_numpy(), proba, test["order_value"].to_numpy(),
                 test["is_cod"].to_numpy())
    assert rep["tau_star"] < 0.5


def test_model_beats_block_all_cod():
    test, proba = _fitted()
    rep = report(test["is_rto"].to_numpy(), proba, test["order_value"].to_numpy(),
                 test["is_cod"].to_numpy())
    assert rep["at_tau_star"]["cost"] < rep["baselines"]["block_all_cod_cost"]
    assert rep["money"]["savings_vs_block_all_cod_pct"] > 0


def test_bmr_beats_naive_baselines():
    test, proba = _fitted()
    y = test["is_rto"].to_numpy()
    value = test["order_value"].to_numpy()
    cm = CostModel()
    bmr = example_dependent_bmr(y, proba, value, cm)
    approve_all = total_cost(np.zeros_like(y, bool), y, value, cm)
    assert bmr["cost"] < approve_all


def test_cost_curve_is_wellformed():
    test, proba = _fitted()
    curve = cost_curve(test["is_rto"].to_numpy(), proba, test["order_value"].to_numpy(),
                       CostModel())
    assert (curve["cost"] >= 0).all()
    assert curve["threshold"].is_monotonic_increasing
