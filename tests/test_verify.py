"""Tests for the cross-vendor adversarial verifier (offline via MockProvider)."""
from __future__ import annotations

import json

from src.agent.investigate import AgentDecision, ToolCall, investigate
from src.agent.llm import MockProvider
from src.agent.tools import OrderContext
from src.agent.verify import verify_decision
from src.rag.policy import PolicyRetriever


def make_ctx(**kw) -> OrderContext:
    base = dict(order_id="O1", is_cod=1, order_value=1200.0, is_serviceable=1, city_tier=2,
                address_completeness=0.35, pincode=560001, pincode_rto_rate=0.31,
                buyer_prior_orders=1, buyer_prior_rto=0.2, is_first_time_buyer=0,
                device_orders_24h=2, buyer_orders_7d=1, device_distinct_buyers_prior=1,
                account_age_days=120, phone_verified=0, risk_score=0.32, anomaly_score=0.2,
                device_id="DEV1")
    base.update(kw)
    return OrderContext(**base)


def _decision() -> AgentDecision:
    return AgentDecision("step_up_verification", 0.7, "borderline COD", False, ["RTO-POL-3.2"],
                         [ToolCall("check_address", {"quality": "partial"})],
                         ["RTO-POL-3.2: amber step-up"], "llm")


def test_verify_agree():
    v = verify_decision(_decision(), make_ctx(), vendor_label="mock · vendorX",
                        provider=MockProvider(canned=json.dumps(
                            {"verdict": "agree", "confidence": 0.8, "reason": "grounded"})))
    assert v["verdict"] == "agree" and v["verifier"] == "mock · vendorX"


def test_verify_rejects_bad_json():
    v = verify_decision(_decision(), make_ctx(), provider=MockProvider(canned="not json"))
    assert v is None


def test_investigate_veto_escalates_to_human():
    retr = PolicyRetriever()
    primary = MockProvider(canned=json.dumps(
        {"action": "step_up_verification", "confidence": 0.7, "requires_human": False,
         "rationale": "verify", "policy_citations": ["RTO-POL-3.2"]}))
    veto = MockProvider(canned=json.dumps(
        {"verdict": "veto", "confidence": 0.9, "reason": "insufficient verification"}))
    dec = investigate(make_ctx(), retr, provider=primary, verifier=veto)
    assert dec.verification and dec.verification["verdict"] == "veto"
    assert dec.requires_human is True


def test_investigate_marks_same_vendor_not_independent():
    # primary and verifier are both the (mock) vendor -> we must NOT claim independence
    retr = PolicyRetriever()
    primary = MockProvider(canned=json.dumps(
        {"action": "step_up_verification", "confidence": 0.7, "requires_human": False,
         "rationale": "verify", "policy_citations": []}))
    agreeing = MockProvider(canned=json.dumps(
        {"verdict": "agree", "confidence": 0.8, "reason": "grounded"}))
    dec = investigate(make_ctx(), retr, provider=primary, verifier=agreeing)
    assert dec.verification is not None
    assert dec.verification["independent"] is False


def test_investigate_verifier_none_skips():
    retr = PolicyRetriever()
    dec = investigate(make_ctx(), retr, verifier=None, provider=MockProvider(canned=json.dumps(
        {"action": "approve", "confidence": 0.7, "requires_human": False, "rationale": "x",
         "policy_citations": []})))
    assert dec.verification is None
