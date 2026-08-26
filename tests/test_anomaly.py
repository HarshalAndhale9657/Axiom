"""Tests for the IsolationForest anomaly layer."""
from __future__ import annotations

import numpy as np
import pytest

from src.data.generate_synthetic_cod import generate
from src.features.build_features import build_features
from src.model.anomaly import AnomalyDetector


@pytest.fixture(scope="module")
def detector_and_data():
    orders, _ = generate(n=6000, seed=0)
    bundle = build_features(orders)
    train = bundle.frame[bundle.frame["split"] == "train"]
    test = bundle.frame[bundle.frame["split"] == "test"]
    det = AnomalyDetector(bundle.feature_columns, bundle.categorical_columns).fit(train)
    return det, test


def test_scores_are_valid_probabilities(detector_and_data):
    det, test = detector_and_data
    s = det.anomaly_score(test)
    assert s.shape[0] == len(test)
    assert np.all(np.isfinite(s))
    assert np.all((s >= 0.0) & (s <= 1.0))


def test_scores_have_spread(detector_and_data):
    """A useful detector must not assign every order the same score."""
    det, test = detector_and_data
    s = det.anomaly_score(test)
    assert s.std() > 0.01


def test_reproducible(detector_and_data):
    det, test = detector_and_data
    s1 = det.anomaly_score(test)
    s2 = det.anomaly_score(test)
    assert np.allclose(s1, s2)
