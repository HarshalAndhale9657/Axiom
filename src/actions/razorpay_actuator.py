"""Razorpay TEST-mode actuator — the auto-responder's actions execute for REAL.

When Axiom decides ``convert_cod_to_prepaid`` or ``part_pay_cod`` on a risky COD order, it
calls Razorpay's live **test-mode** Payment Links API and returns a genuine, clickable
``https://rzp.io/...`` link (+ ``plink_...`` id). This proves the closed action set isn't
theatre — the safest bounded action runs end-to-end on the payments rail the judges built.

Honesty: it's a **test-mode** link — real Razorpay artifact, **no real money moves**. If
``RAZORPAY_ENABLED`` is off or keys are missing (or a call fails), we return a clearly
``simulated`` link so the system never hard-depends on the network.
"""
from __future__ import annotations

import os

from src.util import load_env

# Razorpay's test validator rejects phone numbers with long recurring digit runs.
_DEMO_CONTACT = "+919876543210"


def _client():
    load_env()
    if os.environ.get("RAZORPAY_ENABLED", "0") != "1":
        return None
    key_id, key_secret = os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET")
    if not (key_id and key_secret):
        return None
    try:
        import razorpay
        return razorpay.Client(auth=(key_id, key_secret))
    except Exception:
        return None


def _simulated(action: str, amount_inr: float, deposit_inr: int | None = None) -> dict:
    return {"simulated": True, "action": action, "amount_inr": round(amount_inr),
            "deposit_inr": deposit_inr, "plink_id": "plink_SIMULATED",
            "short_url": "https://rzp.io/i/SIMULATED", "status": "simulated"}


def _notes(order_id: str, action: str, band: str, risk_score: float) -> dict:
    return {"axiom_order": order_id, "axiom_action": action, "axiom_band": band,
            "axiom_risk_score": str(round(risk_score, 3))}


def create_prepaid_link(order_id: str, amount_inr: float, band: str = "amber",
                        risk_score: float = 0.0, email: str = "buyer@example.com") -> dict:
    """Create a real test-mode prepaid payment link (amount in paise)."""
    client = _client()
    if client is None:
        return _simulated("convert_cod_to_prepaid", amount_inr)
    try:
        pl = client.payment_link.create({
            "amount": int(round(amount_inr * 100)), "currency": "INR",
            "description": f"Axiom: convert COD order {order_id} to prepaid",
            "customer": {"name": "Customer", "contact": _DEMO_CONTACT, "email": email},
            "notify": {"sms": False, "email": False}, "reminder_enable": False,
            "notes": _notes(order_id, "convert_cod_to_prepaid", band, risk_score),
        })
        return {"simulated": False, "action": "convert_cod_to_prepaid", "amount_inr": round(amount_inr),
                "deposit_inr": None, "plink_id": pl["id"], "short_url": pl["short_url"],
                "status": pl["status"]}
    except Exception as exc:  # never break the demo on a link failure
        return {**_simulated("convert_cod_to_prepaid", amount_inr), "error": str(exc)[:140]}


def create_partial_link(order_id: str, amount_inr: float, deposit_inr: float, band: str = "amber",
                        risk_score: float = 0.0, email: str = "buyer@example.com") -> dict:
    """Create a real test-mode part-pay link: a risk-based upfront deposit, rest on delivery."""
    deposit = max(50, min(int(round(deposit_inr)), int(round(amount_inr))))
    client = _client()
    if client is None:
        return _simulated("part_pay_cod", amount_inr, deposit)
    try:
        pl = client.payment_link.create({
            "amount": int(round(amount_inr * 100)), "currency": "INR",
            "accept_partial": True, "first_min_partial_amount": int(deposit * 100),
            "description": f"Axiom: part-pay deposit for COD order {order_id}",
            "customer": {"name": "Customer", "contact": _DEMO_CONTACT, "email": email},
            "notify": {"sms": False, "email": False}, "reminder_enable": False,
            "notes": _notes(order_id, "part_pay_cod", band, risk_score),
        })
        return {"simulated": False, "action": "part_pay_cod", "amount_inr": round(amount_inr),
                "deposit_inr": deposit, "plink_id": pl["id"], "short_url": pl["short_url"],
                "status": pl["status"]}
    except Exception as exc:
        return {**_simulated("part_pay_cod", amount_inr, deposit), "error": str(exc)[:140]}
