"""Tests for SHAP explanations (the grounded facts behind reason codes)."""
from __future__ import annotations

import numpy as np
import pytest

from src.data.generate_synthetic_cod import generate
from src.features.build_features import build_features
from src.model.explain import RTOExplainer
from src.model.train import train_model


@pytest.fixture(scope="module")
def explainer_and_data():
    orders, _ = generate(n=6000, seed=0)
    bundle = build_features(orders)
    result = train_model(bundle, params={"n_estimators": 150, "learning_rate": 0.05})
    test = bundle.frame[bundle.frame["split"] == "test"]
    return RTOExplainer(result.model), test, bundle


def test_explain_row_returns_sorted_finite_factors(explainer_and_data):
    explainer, test, bundle = explainer_and_data
    row = test[bundle.feature_columns].iloc[[0]]
    exp = explainer.explain_row(row, top_n=5)
    assert 1 <= len(exp.factors) <= 5
    mags = [abs(f.shap) for f in exp.factors]
    assert mags == sorted(mags, reverse=True)           # sorted by |shap| desc
    assert all(np.isfinite(f.shap) for f in exp.factors)
    assert all(f.direction in {"raises", "lowers"} for f in exp.factors)


def test_grounded_reason_is_nonempty_string(explainer_and_data):
    explainer, test, bundle = explainer_and_data
    row = test[bundle.feature_columns].iloc[[0]]
    reason = explainer.explain_row(row).grounded_reason()
    assert isinstance(reason, str) and len(reason) > 0


def test_global_importance_is_well_formed(explainer_and_data):
    explainer, test, bundle = explainer_and_data
    imp = explainer.global_importance(test[bundle.feature_columns])
    assert set(imp.index) == set(bundle.feature_columns)
    assert (imp >= 0).all() and imp.sum() > 0


def test_explanation_is_deterministic(explainer_and_data):
    explainer, test, bundle = explainer_and_data
    row = test[bundle.feature_columns].iloc[[3]]
    a = explainer.explain_row(row).as_payload()
    b = explainer.explain_row(row).as_payload()
    assert a == b
