"""Tests for the deterministic decision core.

The two guarantees that matter for a defense-only, bounded system: (1) the action space
is closed, and (2) every deterministic rule fires exactly when the policy says -- and
overrides the banded score.
"""
from __future__ import annotations

from src.data.generate_synthetic_cod import generate
from src.features.build_features import build_features
from src.rules.decision_core import ACTIONS, Band, Decision, decide, decide_from_row


def _decide(**kw) -> Decision:
    base = dict(order_id="O1", risk_score=0.3, is_cod=1, order_value=1000.0)
    base.update(kw)
    return decide(**base)


def test_action_always_in_bounded_set():
    for score in [0.01, 0.2, 0.5, 0.95]:
        for cod in (0, 1):
            d = _decide(risk_score=score, is_cod=cod, order_value=2000)
            assert d.action in ACTIONS


def test_rule_nonserviceable_overrides_low_score():
    d = _decide(risk_score=0.01, is_serviceable=0)
    assert d.band == Band.RED and d.action == "hold_for_review"
    assert d.rule_id == "RTO-POL-2.2" and d.requires_human


def test_rule_blocklist():
    d = _decide(risk_score=0.01, device_id="DEV_RING0001",
                blocklist=frozenset({"DEV_RING0001"}))
    assert d.band == Band.RED and d.rule_id == "RTO-POL-2.3" and d.requires_human


def test_rule_velocity_ring():
    d = _decide(risk_score=0.2, device_orders_24h=12)
    assert d.band == Band.RED and d.action == "escalate_to_human"
    assert d.rule_id == "RTO-POL-2.4"


def test_rule_trusted_repeat_prepaid_overrides_high_score():
    """Rules run before banding: a trusted prepaid repeat buyer is approved even at score 0.9."""
    d = _decide(risk_score=0.9, is_cod=0, buyer_prior_orders=5, buyer_prior_rto=0.02)
    assert d.band == Band.GREEN and d.action == "approve" and d.rule_id == "RTO-POL-2.1"


def test_banding_green_amber_red():
    assert _decide(risk_score=0.05).band == Band.GREEN
    assert _decide(risk_score=0.30).band == Band.AMBER
    assert _decide(risk_score=0.70).band == Band.RED


def test_amber_cod_uses_dynamic_friction():
    d = _decide(risk_score=0.30, is_cod=1)
    assert d.band == Band.AMBER and d.action == "step_up_verification"


def test_red_high_value_escalates_to_human():
    d = _decide(risk_score=0.70, is_cod=1, order_value=8000)
    assert d.action == "escalate_to_human" and d.requires_human


def test_red_cod_converts_to_prepaid():
    d = _decide(risk_score=0.70, is_cod=1, order_value=1500)
    assert d.action == "convert_cod_to_prepaid"


def test_anomaly_tripwire_bumps_green_to_amber():
    calm = _decide(risk_score=0.05, anomaly_score=0.10)
    tripped = _decide(risk_score=0.05, anomaly_score=0.95)
    assert calm.band == Band.GREEN
    assert tripped.band == Band.AMBER


def test_decide_from_row_integration():
    orders, _ = generate(n=3000, seed=0)
    bundle = build_features(orders)
    row = bundle.frame.iloc[0]
    d = decide_from_row(row, risk_score=0.30, anomaly_score=0.1)
    assert d.action in ACTIONS and d.band in {Band.GREEN, Band.AMBER, Band.RED}
