"""Deterministic decision core for Axiom — the bounded, auditable backbone.

Mirrors how Razorpay's own systems work (Bumblebee / Capital): **deterministic rules run
first** (highest precision, fully explainable), then the calibrated score is banded by
**cost-optimal thresholds** into GREEN / AMBER / RED, and each band maps to a **bounded**
action. An unsupervised anomaly score acts as an independent trip-wire that can escalate an
otherwise-green order.

The LLM agent (later) only *investigates the AMBER band* and may recommend within this same
bounded action space -- it can never invent an action or override a hard rule. Every rule
cites a clause from ``docs/policy/rto_cod_risk_policy.md``.

This module has **no ML/LLM dependency** and is exhaustively unit-tested: the action space
is closed, and every terminal rule fires exactly when the policy says it should.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


class Band:
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


# The complete, closed set of actions the system can ever take (defense-only).
ACTIONS = frozenset({
    "approve", "step_up_verification", "part_pay_cod", "convert_cod_to_prepaid",
    "hold_for_review", "escalate_to_human",
})


@dataclass(frozen=True)
class DecisionConfig:
    tau_low: float = 0.15          # below -> GREEN
    tau_high: float = 0.45         # at/above -> RED  (AMBER in between)
    anomaly_escalate: float = 0.90  # high anomaly trips GREEN -> AMBER (cold-start guard)
    ring_velocity_24h: int = 8     # > this many orders/device/24h -> ring (RED)
    high_value: float = 5000.0     # RED on a high-value order escalates to a human
    repeat_min_orders: int = 3     # trusted repeat buyer: prior delivered orders
    repeat_max_rto: float = 0.05   # ...and prior RTO rate below this


@dataclass
class Decision:
    order_id: str
    risk_score: float
    anomaly_score: float
    band: str
    action: str
    action_detail: str
    reason: str
    confidence: float
    requires_human: bool
    rule_id: str | None = None                    # deterministic rule that fired, if any
    policy_citations: list[str] = field(default_factory=list)
    top_factors: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        assert self.action in ACTIONS, f"illegal action {self.action!r}"
        assert self.band in {Band.GREEN, Band.AMBER, Band.RED}

    def as_dict(self) -> dict:
        return {
            "order_id": self.order_id, "risk_score": round(self.risk_score, 4),
            "anomaly_score": round(self.anomaly_score, 4), "band": self.band,
            "action": self.action, "action_detail": self.action_detail,
            "reason": self.reason, "confidence": round(self.confidence, 3),
            "requires_human": self.requires_human, "rule_id": self.rule_id,
            "policy_citations": self.policy_citations, "top_factors": self.top_factors,
        }


def _band_confidence(score: float, cfg: DecisionConfig, band: str) -> float:
    if band == Band.GREEN:
        return float(min(0.95, 0.6 + 0.35 * (cfg.tau_low - score) / max(cfg.tau_low, 1e-6)))
    if band == Band.RED:
        return float(min(0.95, 0.6 + 0.35 * (score - cfg.tau_high) / max(1 - cfg.tau_high, 1e-6)))
    return 0.6  # AMBER is borderline by definition


def decide(
    *,
    order_id: str,
    risk_score: float,
    is_cod: bool | int,
    order_value: float,
    is_serviceable: bool | int = 1,
    device_orders_24h: int = 0,
    buyer_prior_orders: int = 0,
    buyer_prior_rto: float = 0.0,
    anomaly_score: float = 0.0,
    device_id: str | None = None,
    phone: str | None = None,
    explanation=None,                    # src.model.explain.Explanation | None
    blocklist: frozenset[str] = frozenset(),
    config: DecisionConfig | None = None,
) -> Decision:
    """Return the bounded, policy-cited decision for a single order."""
    cfg = config or DecisionConfig()
    is_cod = bool(is_cod)
    reason_from_shap = explanation.grounded_reason() if explanation is not None else None
    top_factors = explanation.as_payload() if explanation is not None else []

    def build(band, action, detail, reason, conf, requires_human, rule_id, cites):
        return Decision(order_id, float(risk_score), float(anomaly_score), band, action,
                        detail, reason, float(conf), bool(requires_human), rule_id,
                        list(cites), top_factors)

    # ---- 1. Deterministic rules (run BEFORE banding; highest precision) --------------
    if (device_id and device_id in blocklist) or (phone and phone in blocklist):
        return build(Band.RED, "hold_for_review",
                     "Entity on the confirmed-abuse blocklist; hold and escalate.",
                     "Blocked: device/phone on the confirmed-abuse list.", 0.95, True,
                     "RTO-POL-2.3", ["RTO-POL-2.3"])

    if not bool(is_serviceable):
        return build(Band.RED, "hold_for_review",
                     "Delivery pincode is non-serviceable; hold for review (never silently fail).",
                     "Blocked: delivery pincode is non-serviceable.", 0.9, True,
                     "RTO-POL-2.2", ["RTO-POL-2.2"])

    if device_orders_24h > cfg.ring_velocity_24h:
        return build(Band.RED, "escalate_to_human",
                     f"{device_orders_24h} orders from this device in 24h — fraud-ring velocity.",
                     "Blocked: fraud-ring velocity on this device.", 0.9, True,
                     "RTO-POL-2.4", ["RTO-POL-2.4"])

    if (not is_cod) and buyer_prior_orders >= cfg.repeat_min_orders \
            and buyer_prior_rto < cfg.repeat_max_rto:
        return build(Band.GREEN, "approve",
                     "Trusted repeat buyer on prepaid; frictionless approve.",
                     "Trusted repeat buyer on prepaid.", 0.95, False,
                     "RTO-POL-2.1", ["RTO-POL-2.1"])

    # ---- 2. Band by cost-optimal thresholds -----------------------------------------
    if risk_score < cfg.tau_low:
        band = Band.GREEN
    elif risk_score >= cfg.tau_high:
        band = Band.RED
    else:
        band = Band.AMBER

    # anomaly trip-wire: an otherwise-green but highly anomalous order gets a look
    anomaly_bumped = False
    if band == Band.GREEN and anomaly_score >= cfg.anomaly_escalate:
        band, anomaly_bumped = Band.AMBER, True

    reason = reason_from_shap or {
        Band.GREEN: "Low predicted RTO risk.",
        Band.AMBER: "Borderline RTO risk — verify before dispatch.",
        Band.RED: "High predicted RTO risk.",
    }[band]
    if anomaly_bumped:
        reason = "Unusual order pattern (anomaly trip-wire) — verify. " + reason

    # ---- 3. Bounded action per band (dynamic friction) ------------------------------
    cites = ["RTO-POL-1"]
    if band == Band.GREEN:
        action, detail = "approve", "Frictionless approve."
        cites.append("RTO-POL-3.1")
        requires_human = False
    elif band == Band.AMBER:
        cites += ["RTO-POL-3.2", "RTO-POL-3.0"]
        if is_cod:
            action = "step_up_verification"
            detail = ("Dynamic friction: send COD-confirmation OTP / address check; "
                      "offer prepaid link or a small part-pay deposit.")
        else:
            action = "step_up_verification"
            detail = "Dynamic friction: lightweight verification before dispatch."
        requires_human = False
    else:  # RED
        cites.append("RTO-POL-3.3")
        if order_value > cfg.high_value:
            action = "escalate_to_human"
            detail = "High-value, high-risk order — route to a human reviewer."
            requires_human = True
        elif is_cod:
            action = "convert_cod_to_prepaid"
            detail = "Convert COD to prepaid (payment link) or hold; protect the merchant."
            requires_human = False
        else:
            action = "hold_for_review"
            detail = "Hold the order for review."
            requires_human = False

    return build(band, action, detail, reason, _band_confidence(risk_score, cfg, band),
                 requires_human, None, cites)


def decide_from_row(row: pd.Series, risk_score: float, anomaly_score: float = 0.0,
                    explanation=None, blocklist: frozenset[str] = frozenset(),
                    config: DecisionConfig | None = None) -> Decision:
    """Convenience adapter from a built-feature row (maps log-counts back to counts)."""
    import numpy as np

    return decide(
        order_id=str(row.get("order_id", "NA")),
        risk_score=risk_score,
        is_cod=int(row.get("is_cod", 0)),
        order_value=float(row.get("order_value", 0.0)),
        is_serviceable=int(row.get("is_serviceable", 1)),
        device_orders_24h=int(row.get("device_orders_24h", 0)),
        buyer_prior_orders=int(round(np.expm1(row.get("buyer_orders_prior_log", 0.0)))),
        buyer_prior_rto=float(row.get("buyer_rto_enc", 0.0)),
        anomaly_score=anomaly_score,
        device_id=row.get("device_id"),
        phone=row.get("phone"),
        explanation=explanation,
        blocklist=blocklist,
        config=config,
    )
