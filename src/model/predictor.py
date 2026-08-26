"""Serving-time artifact: a LightGBM booster wrapped with an isotonic calibrator.

This class lives in its own module -- one that is only ever *imported*, never executed
as ``__main__`` -- so the pickled object always has a stable import path
(``src.model.predictor.CalibratedRTOModel``). That avoids the classic ``__main__``
pickling pitfall where an artifact saved by ``python -m src.model.train`` cannot be
loaded by another entrypoint.
"""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


class CalibratedRTOModel:
    """A fitted LightGBM wrapped with an isotonic calibrator. Predicts calibrated P(RTO)."""

    def __init__(self, booster: lgb.LGBMClassifier, calibrator: IsotonicRegression,
                 feature_columns: list[str], categorical_columns: list[str]) -> None:
        self.booster = booster
        self.calibrator = calibrator
        self.feature_columns = feature_columns
        self.categorical_columns = categorical_columns

    def _raw(self, X: pd.DataFrame) -> np.ndarray:
        return self.booster.predict_proba(X[self.feature_columns])[:, 1]

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Calibrated P(RTO) in [0, 1]."""
        return self.calibrator.predict(self._raw(X))
