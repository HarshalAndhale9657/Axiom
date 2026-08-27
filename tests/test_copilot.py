"""Tests for the grounded analyst copilot (offline via MockProvider)."""
from __future__ import annotations

import json

from src.agent.copilot import answer, build_context
from src.agent.llm import MockProvider

ORDER = {
    "payment_method": "COD", "order_value": 1200, "product_category": "electronics",
    "city": "Bengaluru", "city_tier": 2, "pincode": 560001, "distance_km": 12,
    "address_completeness": 0.35, "is_first_time_buyer": 0, "account_age_days": 120,
    "phone_verified": 0,
}
DECISION = {
    "order_id": "ORD1", "action": "step_up_verification", "band": "amber",
    "reason": "Borderline COD; verify before dispatch.", "policy_citations": ["RTO-POL-3.2"],
    "top_factors": [{"feature": "address_completeness", "label": "Address quality",
                     "direction": "raises"}],
}
POLICY = ["RTO-POL-3.2: amber orders -> step-up verification before dispatch."]


def test_build_context_only_uses_case_facts():
    ctx = build_context(order=ORDER, risk_score=0.32, anomaly_score=0.2, band="amber",
                        decision=DECISION, factors=DECISION["top_factors"], policy=POLICY)
    assert "560001" in ctx and "RTO-POL-3.2" in ctx and "amber" in ctx
    assert "step_up_verification" in ctx


def test_answer_returns_grounded_citations():
    prov = MockProvider(canned=json.dumps(
        {"answer": "It's amber because the address is only 35% complete and the pincode RTO rate "
                   "is elevated; policy RTO-POL-3.2 calls for step-up verification.",
         "policy_citations": ["RTO-POL-3.2"]}))
    res = answer("Why was this flagged?", order=ORDER, risk_score=0.32, anomaly_score=0.2,
                 band="amber", decision=DECISION, factors=DECISION["top_factors"], policy=POLICY,
                 provider=prov)
    assert res["grounded"] is True
    assert res["citations"] == ["RTO-POL-3.2"]           # kept: it was actually on file
    assert "35%" in res["answer"]


def test_answer_drops_invented_citations():
    prov = MockProvider(canned=json.dumps(
        {"answer": "Not in the record.", "policy_citations": ["RTO-POL-9.9-made-up"]}))
    res = answer("What is the buyer's shoe size?", order=ORDER, risk_score=0.32, anomaly_score=0.2,
                 band="amber", decision=DECISION, factors=DECISION["top_factors"], policy=POLICY,
                 provider=prov)
    assert res["citations"] == []                        # invented id is filtered out


def test_answer_handles_bad_json_gracefully():
    res = answer("Why?", order=ORDER, risk_score=0.32, anomaly_score=0.2, band="amber",
                 decision=DECISION, factors=[], policy=POLICY,
                 provider=MockProvider(canned="not json at all"))
    assert res["grounded"] is False and res["citations"] == []
