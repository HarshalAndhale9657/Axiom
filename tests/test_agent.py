"""Tests for the bounded investigation agent (offline via MockProvider).

Guarantees: tools return structured evidence, the agent honours the closed action set, and
it always degrades to a deterministic bounded decision when the LLM misbehaves or is down.
"""
from __future__ import annotations

import json

import pytest

from src.agent.investigate import AMBER_ACTIONS, ToolCall, investigate, plan_tools
from src.agent.llm import LLMError, MockProvider
from src.agent.tools import TOOLS, OrderContext
from src.rag.policy import PolicyRetriever
from src.rules.decision_core import ACTIONS


def make_ctx(**kw) -> OrderContext:
    base = dict(
        order_id="O1", is_cod=1, order_value=1200.0, is_serviceable=1, city_tier=2,
        address_completeness=0.35, pincode=560001, pincode_rto_rate=0.31,
        buyer_prior_orders=1, buyer_prior_rto=0.2, is_first_time_buyer=0,
        device_orders_24h=2, buyer_orders_7d=1, device_distinct_buyers_prior=1,
        account_age_days=120, phone_verified=0, risk_score=0.32, anomaly_score=0.2,
        device_id="DEV1",
    )
    base.update(kw)
    return OrderContext(**base)


@pytest.fixture(scope="module")
def retriever() -> PolicyRetriever:
    return PolicyRetriever()


def test_tools_return_structured_evidence():
    ctx = make_ctx()
    assert set(TOOLS) == {"get_buyer_history", "check_address", "get_pincode_risk",
                          "check_velocity"}
    assert TOOLS["check_address"](ctx)["quality"] in {"good", "partial", "poor"}
    assert "ring_suspected" in TOOLS["check_velocity"](ctx)


def test_plan_includes_core_tools():
    plan = plan_tools(make_ctx())
    assert {"check_address", "get_pincode_risk", "get_buyer_history"} <= set(plan)


def test_agent_accepts_valid_llm_json(retriever):
    canned = json.dumps({"action": "step_up_verification", "confidence": 0.72,
                         "requires_human": False, "rationale": "Borderline COD; verify.",
                         "policy_citations": ["RTO-POL-3.2"]})
    dec = investigate(make_ctx(), retriever, provider=MockProvider(canned=canned))
    assert dec.source == "llm"
    assert dec.action == "step_up_verification" and dec.action in ACTIONS
    assert dec.policy_citations == ["RTO-POL-3.2"]
    assert dec.evidence and dec.retrieved_policy


def test_agent_rejects_out_of_bounds_action_and_falls_back(retriever):
    canned = json.dumps({"action": "delete_customer", "confidence": 0.9,
                         "requires_human": False, "rationale": "x", "policy_citations": []})
    dec = investigate(make_ctx(), retriever, provider=MockProvider(canned=canned))
    assert dec.source == "fallback"
    assert dec.action in ACTIONS


def test_agent_falls_back_on_llm_error(retriever):
    class Boom:
        def generate(self, *a, **k):
            raise LLMError("down")

    dec = investigate(make_ctx(), retriever, provider=Boom())
    assert dec.source == "fallback" and dec.action in ACTIONS
    assert dec.evidence            # evidence is still gathered even without the LLM


def test_agent_action_always_bounded(retriever):
    # even a garbage (non-JSON) response must yield a bounded decision
    dec = investigate(make_ctx(), retriever, provider=MockProvider(canned="not json"))
    assert dec.action in ACTIONS
