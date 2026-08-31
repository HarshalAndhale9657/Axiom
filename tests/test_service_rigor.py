"""The evidence endpoints the dashboard reads: thresholds, ablation, harm audit, model card.

The engine here loads the *shipped* model directory, so these also act as a smoke test that
what is committed in ``models/`` is coherent with the code that serves it.
"""
from __future__ import annotations

import json

import pytest

from src.agent.llm import MockProvider
from src.api.service import RiskEngine
from src.data.generate_synthetic_cod import generate
from src.rules.decision_core import DecisionConfig

CANNED = json.dumps({"action": "step_up_verification", "confidence": 0.7,
                     "requires_human": False, "rationale": "Borderline COD.",
                     "policy_citations": ["RTO-POL-3.2"]})


@pytest.fixture(scope="module")
def engine(tmp_path_factory) -> RiskEngine:
    orders, _ = generate(n=5000, seed=0)
    audit = tmp_path_factory.mktemp("audit") / "audit.sqlite"
    return RiskEngine(orders=orders, audit_path=str(audit),
                      provider=MockProvider(canned=CANNED), queue_limit=40)


def test_engine_serves_the_frozen_operating_point(engine):
    """The bands the service applies must be the ones fitted on validation, not defaults."""
    assert engine.thresholds is not None, "models/thresholds.json is missing — retrain"
    assert engine.thresholds.fitted_on == "val"
    assert engine.config.tau_low == pytest.approx(engine.thresholds.tau_low)
    assert engine.config.tau_high == pytest.approx(engine.thresholds.tau_high)
    assert (engine.config.tau_low, engine.config.tau_high) != (
        DecisionConfig().tau_low, DecisionConfig().tau_high)


def test_metrics_are_scored_at_the_frozen_threshold_with_intervals(engine):
    m = engine.metrics(n_boot=40)
    assert m["tau_source"] == "val_frozen"
    assert m["tau_star"] == pytest.approx(engine.thresholds.tau_star)
    assert m["ci"]["pr_auc"]["lo"] < m["pr_auc"] < m["ci"]["pr_auc"]["hi"]
    assert m["optimism"]["cost_gap"] >= 0


def test_metrics_are_cached_not_recomputed(engine):
    """A fixed model on a fixed split has fixed numbers; recomputing them per request is waste."""
    assert engine.metrics() is engine.metrics()


def test_threshold_report_shows_its_work(engine):
    t = engine.threshold_report()
    assert t["thresholds"]["fitted_on"] == "val"
    assert t["saving_per_1k_vs_hardcoded"] >= 0
    assert len(t["sensitivity"]) > 1, "the assumption sweep must actually vary something"


def test_cost_curve_exposes_both_the_frozen_and_the_oracle_threshold(engine):
    c = engine.cost_curve_points(n_grid=20)
    assert c["tau_source"] == "val_frozen"
    assert c["optimism_cost_gap_per_1k"] >= 0
    assert c["tau_low"] < c["tau_high"]
    assert len(c["points"]) == 20


def test_baseline_report_names_a_real_opponent(engine):
    rows = engine.baseline_report(n_boot=0)["rows"]
    names = {r["model"] for r in rows}
    assert {"rules-only scorecard", "logistic regression", "LightGBM (Axiom)"} <= names
    assert all(r["tau_val_fitted"] < 0.5 for r in rows)


def test_slice_report_identifies_who_absorbs_the_friction(engine):
    s = engine.slice_report()
    assert s["slices"] and s["worst"]
    assert all(0.0 <= r["fp_rate_on_good"] <= 1.0 for r in s["slices"])
    top = s["disparity"][0]
    # An undefined ratio (no false positives in the safest slice) is reported as such.
    assert top["unbounded"] or top["ratio"] >= 1.0


def test_model_meta_declares_provenance_and_no_protected_attributes(engine):
    meta = engine.model_meta()
    assert meta["protected_attributes_used"] == [] and meta["pii_used"] == []
    assert meta["outcome_lag_days"] == 7.0
    assert "synthetic" in meta["data_provenance"]
    assert meta["split"]["policy"].startswith("chronological")
    assert meta["out_of_scope"], "a model card without out-of-scope uses is not a model card"


def test_every_evidence_endpoint_is_json_serialisable(engine):
    """FastAPI will 500 on a stray numpy scalar or NaN; catch it here instead."""
    for payload in (engine.metrics(n_boot=20), engine.threshold_report(),
                    engine.baseline_report(n_boot=0), engine.slice_report(),
                    engine.model_meta(), engine.cost_curve_points(n_grid=10)):
        text = json.dumps(payload, allow_nan=False)
        assert text
