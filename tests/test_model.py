"""Smoke tests for the baseline calibrated LightGBM RTO model.

Fast by design (small data, few trees). Guarantees: calibrated probabilities are valid,
the model beats the no-skill PR baseline, and save/load round-trips exactly.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.data.generate_synthetic_cod import generate
from src.features.build_features import build_features
from src.model.train import load, save, train_model

FAST_PARAMS = {"n_estimators": 200, "learning_rate": 0.05}


@pytest.fixture(scope="module")
def result():
    orders, _ = generate(n=8000, seed=0)
    bundle = build_features(orders)
    return train_model(bundle, params=FAST_PARAMS)


def test_probabilities_are_valid(result):
    X_te, _ = result.bundle.split("test")
    p = result.model.predict_proba(X_te)
    assert p.shape[0] == len(X_te)
    assert np.all((p >= 0.0) & (p <= 1.0))


def test_beats_no_skill_baseline(result):
    """PR-AUC must clear the prevalence baseline by a clear margin (real signal)."""
    test = result.metrics["test"]
    assert test["pr_auc"] > test["prevalence"] * 1.5
    assert test["roc_auc"] > 0.65


def test_reasonably_calibrated(result):
    """Isotonic calibration should keep the Brier score well below the prevalence floor."""
    test = result.metrics["test"]
    assert test["brier"] < test["prevalence"]


def test_save_load_roundtrip(tmp_path, result):
    save(result, tmp_path)
    loaded = load(tmp_path)
    X_te, _ = result.bundle.split("test")
    p1 = result.model.predict_proba(X_te)
    p2 = loaded["model"].predict_proba(X_te)
    assert np.allclose(p1, p2)
    assert loaded["feature_columns"] == result.bundle.feature_columns
