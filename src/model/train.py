"""Baseline RTO risk model for Axiom: calibrated LightGBM.

Design decisions (defensible in the pitch)
------------------------------------------
* **Natural distribution, no resampling.** RTO here is ~19% positive -- *moderate*
  imbalance, not the <1% extreme. Resampling/《class weights》 distort predicted
  probabilities, and our entire cost story (BMR threshold on calibrated probabilities)
  depends on those probabilities meaning what they say. So we train on the real
  distribution and get honesty from **isotonic calibration + cost-based thresholding**.
* **Isotonic calibration on the validation split.** The raw GBDT scores are mapped to
  true frequencies via a monotone fit on val; the **test split stays untouched** until
  the final report.
* **Early stopping on val** (PR-AUC), so tree count is chosen honestly, not guessed.

This module trains, calibrates, evaluates on the held-out test split, and persists the
artifact. The full honest-metrics story (BMR rupee curve, failure modes) lives in the
evaluation notebook; here we report the headline PR-AUC baseline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src.features.build_features import FeatureBundle, build_features
from src.model.predictor import CalibratedRTOModel

DEFAULT_PARAMS: dict = {
    "objective": "binary",
    "n_estimators": 600,
    "learning_rate": 0.03,
    "num_leaves": 31,
    "min_child_samples": 60,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "verbose": -1,
}


@dataclass
class TrainResult:
    model: CalibratedRTOModel
    metrics: dict
    bundle: FeatureBundle
    best_iteration: int = 0
    importances: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))


def evaluate(y_true: np.ndarray, proba: np.ndarray) -> dict:
    """Honest headline metrics for an imbalanced problem (accuracy intentionally absent)."""
    prevalence = float(np.mean(y_true))
    pr_auc = float(average_precision_score(y_true, proba))
    return {
        "n": int(len(y_true)),
        "prevalence": prevalence,          # the PR-curve no-skill baseline
        "pr_auc": pr_auc,
        "pr_auc_lift_over_baseline": pr_auc / prevalence if prevalence else float("nan"),
        "roc_auc": float(roc_auc_score(y_true, proba)),
        "brier": float(brier_score_loss(y_true, proba)),  # lower = better calibrated
    }


def train_model(bundle: FeatureBundle, params: dict | None = None) -> TrainResult:
    """Fit LightGBM on train, calibrate on val, evaluate on the untouched test split."""
    params = {**DEFAULT_PARAMS, **(params or {})}
    X_tr, y_tr = bundle.split("train")
    X_val, y_val = bundle.split("val")
    X_te, y_te = bundle.split("test")

    booster = lgb.LGBMClassifier(**params)
    booster.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        eval_metric="average_precision",
        categorical_feature=bundle.categorical_columns,
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
    )

    # Isotonic calibration on val (test stays untouched).
    raw_val = booster.predict_proba(X_val)[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(raw_val, y_val.to_numpy())

    model = CalibratedRTOModel(booster, calibrator, bundle.feature_columns,
                               bundle.categorical_columns)

    metrics = {
        "val": evaluate(y_val.to_numpy(), model.predict_proba(X_val)),
        "test": evaluate(y_te.to_numpy(), model.predict_proba(X_te)),
    }
    importances = pd.Series(booster.feature_importances_, index=bundle.feature_columns) \
        .sort_values(ascending=False)
    return TrainResult(model, metrics, bundle, int(booster.best_iteration_ or params[
        "n_estimators"]), importances)


def save(result: TrainResult, model_dir: str | Path = "models") -> Path:
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / "axiom_rto_model.joblib"
    joblib.dump(
        {
            "model": result.model,
            "metrics": result.metrics,
            "feature_columns": result.bundle.feature_columns,
            "categorical_columns": result.bundle.categorical_columns,
            "train_meta": result.bundle.meta,
        },
        path,
    )
    return path


def load(model_dir: str | Path = "models") -> dict:
    return joblib.load(Path(model_dir) / "axiom_rto_model.joblib")


def _fmt(m: dict) -> str:
    return (f"PR-AUC {m['pr_auc']:.4f} (baseline {m['prevalence']:.4f}, "
            f"{m['pr_auc_lift_over_baseline']:.1f}x)  |  ROC-AUC {m['roc_auc']:.4f}  |  "
            f"Brier {m['brier']:.4f}  |  n={m['n']:,}")


def main() -> None:
    import argparse

    from src.util import enable_utf8_stdout

    enable_utf8_stdout()
    ap = argparse.ArgumentParser(description="Train the calibrated LightGBM RTO model.")
    ap.add_argument("--in", dest="inp", default="data/cod_orders.csv")
    ap.add_argument("--model-dir", default="models")
    args = ap.parse_args()

    from src.model.threshold import fit_thresholds, save_thresholds, sensitivity

    orders = pd.read_csv(args.inp)
    bundle = build_features(orders)
    result = train_model(bundle)
    path = save(result, args.model_dir)

    # Freeze the operating point on VAL, right here, before anyone looks at test again.
    X_val, y_val = bundle.split("val")
    thresholds = fit_thresholds(y_val.to_numpy(), result.model.predict_proba(X_val),
                                bundle.frame.loc[X_val.index, "order_value"].to_numpy())
    threshold_path = save_thresholds(thresholds, args.model_dir)

    print("=" * 74)
    print("AXIOM — baseline calibrated LightGBM (RTO risk)")
    print("=" * 74)
    print(f"trees used (early-stopped): {result.best_iteration}")
    print(f"VAL   {_fmt(result.metrics['val'])}")
    print(f"TEST  {_fmt(result.metrics['test'])}")
    print("-" * 74)
    print("top 10 feature importances:")
    for name, imp in result.importances.head(10).items():
        print(f"    {name:<30} {int(imp)}")
    print("-" * 74)
    print("OPERATING POINT — fitted on VAL only, then frozen (test is scored once, later):")
    print(f"    binary τ*        : {thresholds.tau_star:.3f}")
    print(f"    band cut-points  : green < {thresholds.tau_low:.3f} <= amber < "
          f"{thresholds.tau_high:.3f} <= red")
    band_range = sensitivity(bundle.frame.loc[X_val.index, "order_value"].to_numpy())
    print(f"    assumption sweep : τ_low ∈ [{band_range['tau_low'].min():.2f}, "
          f"{band_range['tau_low'].max():.2f}], τ_high ∈ [{band_range['tau_high'].min():.2f}, "
          f"{band_range['tau_high'].max():.2f}] across plausible action-efficacy values")
    print(f"    outcome lag      : {bundle.meta['outcome_lag_days']:.0f} days "
          "(label-derived history is held back this long)")
    print("-" * 74)
    print(f"saved -> {path}")
    print(f"saved -> {threshold_path}")
    print("NOTE: accuracy is intentionally NOT reported (useless under imbalance). "
          "The BMR rupee cost curve is the headline — see the evaluation notebook.")


if __name__ == "__main__":
    main()
