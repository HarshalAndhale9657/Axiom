"""Tests for the Razorpay actuator (stub path only — never touches the live API)."""
from __future__ import annotations

from src.actions.razorpay_actuator import create_partial_link, create_prepaid_link


def test_stub_prepaid_link():
    r = create_prepaid_link("ORD1", 500.0)
    assert r["simulated"] is True
    assert r["action"] == "convert_cod_to_prepaid"
    assert r["short_url"].startswith("https://rzp.io/")


def test_stub_partial_link_deposit_bounds():
    r = create_partial_link("ORD1", 1000.0, 5.0)  # tiny deposit is floored to 50
    assert r["simulated"] is True
    assert 50 <= r["deposit_inr"] <= 1000
    assert r["action"] == "part_pay_cod"
