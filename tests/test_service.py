"""Tests for the RiskEngine orchestrator (offline via MockProvider)."""
from __future__ import annotations

import json

import pytest

from src.agent.llm import MockProvider
from src.api.service import RiskEngine
from src.data.generate_synthetic_cod import generate
from src.rules.decision_core import ACTIONS

VALID_AGENT_JSON = json.dumps({
    "action": "step_up_verification", "confidence": 0.7, "requires_human": False,
    "rationale": "Borderline COD; verify before dispatch.", "policy_citations": ["RTO-POL-3.2"],
})


@pytest.fixture(scope="module")
def engine(tmp_path_factory) -> RiskEngine:
    orders, _ = generate(n=5000, seed=0)
    audit = tmp_path_factory.mktemp("audit") / "audit.sqlite"
    return RiskEngine(orders=orders, audit_path=str(audit),
                      provider=MockProvider(canned=VALID_AGENT_JSON), queue_limit=40)


def test_queue_view(engine):
    q = engine.queue_view(limit=25)
    assert 0 < len(q) <= 25
    row = q[0]
    assert row["band"] in {"green", "amber", "red"} and row["action"] in ACTIONS
    assert row["rupee_at_risk"] > 0


def test_assess_returns_detail_with_factors(engine):
    oid = engine.queue_view(limit=5)[0]["order_id"]
    detail = engine.assess(oid)
    assert detail["order_id"] == oid
    assert detail["decision"]["action"] in ACTIONS
    assert detail["decision"]["top_factors"]          # SHAP factors present
    assert "order_value" in detail["order"]


def test_investigate_persists_to_audit(engine):
    oid = engine.queue_view(limit=10)[0]["order_id"]
    result = engine.investigate(oid)
    assert isinstance(result["decision_id"], int)
    assert result["action"] in ACTIONS and result["source"] == "llm"
    logged = engine.audit_log(limit=5)
    assert any(d["id"] == result["decision_id"] for d in logged)


def test_override_is_logged(engine):
    oid = engine.queue_view(limit=10)[0]["order_id"]
    decision_id = engine.investigate(oid)["decision_id"]
    ov = engine.override(decision_id, reviewer="analyst_1", to_action="approve",
                         reason="verified good customer")
    assert ov["to_action"] == "approve"
    logged = {d["id"]: d for d in engine.audit_log(limit=20)}
    assert logged[decision_id]["overrides"][0]["to_action"] == "approve"


def test_metrics_has_money_story(engine):
    m = engine.metrics()
    assert "pr_auc" in m and "money" in m
    assert m["money"]["model_cost_per_1k"] > 0
