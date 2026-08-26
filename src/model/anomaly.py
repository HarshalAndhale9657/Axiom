"""Unsupervised anomaly layer (IsolationForest) — defense-in-depth for Axiom.

The supervised LightGBM learns *known* RTO patterns from labels. An IsolationForest adds
a complementary, label-free view: it flags orders that sit far from the manifold of
normal commerce, catching **zero-day tactics and cold-start entities** that the
supervised model has never seen a label for. In the decision core this becomes an
independent trip-wire (high anomaly can escalate an otherwise-green order to review).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """IsolationForest over the (numeric-encoded) feature matrix, scored to [0, 1]."""

    def __init__(self, feature_columns: list[str], categorical_columns: list[str],
                 n_estimators: int = 200, seed: int = 42) -> None:
        self.feature_columns = feature_columns
        self.categorical_columns = categorical_columns
        self.iso = IsolationForest(
            n_estimators=n_estimators, contamination="auto", random_state=seed, n_jobs=-1
        )
        self._lo = 0.0
        self._hi = 1.0

    def _numeric(self, X: pd.DataFrame) -> pd.DataFrame:
        """Encode categoricals to integer codes so the forest sees an all-numeric matrix."""
        Xn = X[self.feature_columns].copy()
        for col in self.categorical_columns:
            Xn[col] = Xn[col].astype("category").cat.codes
        return Xn

    def fit(self, X_train: pd.DataFrame) -> "AnomalyDetector":
        Xn = self._numeric(X_train)
        self.iso.fit(Xn)
        raw = -self.iso.score_samples(Xn)               # higher = more anomalous
        self._lo, self._hi = float(raw.min()), float(raw.max())
        return self

    def anomaly_score(self, X: pd.DataFrame) -> np.ndarray:
        """Normalised anomaly score in [0, 1] (higher = more anomalous), clipped to train range."""
        raw = -self.iso.score_samples(self._numeric(X))
        return np.clip((raw - self._lo) / (self._hi - self._lo + 1e-9), 0.0, 1.0)
