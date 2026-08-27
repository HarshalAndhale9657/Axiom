"""Typed investigation tools for the Axiom agent.

Each tool is a small, deterministic function that returns structured evidence about one
facet of an order (buyer history, address, pincode risk, velocity). The agent plans which
tools to run, and every call is recorded in the audit trail. Tools read from an
``OrderContext`` assembled from the leakage-safe feature row — so the agent sees exactly
what the scorer saw, nothing more.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class OrderContext:
    order_id: str
    is_cod: int
    order_value: float
    is_serviceable: int
    city_tier: int
    address_completeness: float
    pincode: int
    pincode_rto_rate: float
    buyer_prior_orders: int
    buyer_prior_rto: float
    is_first_time_buyer: int
    device_orders_24h: int
    buyer_orders_7d: int
    device_distinct_buyers_prior: int
    account_age_days: int
    phone_verified: int
    risk_score: float
    anomaly_score: float
    device_id: str | None = None

    @classmethod
    def from_feature_row(cls, row: pd.Series, risk_score: float,
                         anomaly_score: float = 0.0) -> "OrderContext":
        return cls(
            order_id=str(row.get("order_id", "NA")),
            is_cod=int(row.get("is_cod", 0)),
            order_value=float(row.get("order_value", 0.0)),
            is_serviceable=int(row.get("is_serviceable", 1)),
            city_tier=int(row.get("city_tier", 0)),
            address_completeness=float(row.get("address_completeness", 1.0)),
            pincode=int(row.get("pincode", 0)),
            pincode_rto_rate=float(row.get("pincode_rto_enc", 0.0)),
            buyer_prior_orders=int(round(np.expm1(row.get("buyer_orders_prior_log", 0.0)))),
            buyer_prior_rto=float(row.get("buyer_rto_enc", 0.0)),
            is_first_time_buyer=int(row.get("is_first_time_buyer", 0)),
            device_orders_24h=int(row.get("device_orders_24h", 0)),
            buyer_orders_7d=int(row.get("buyer_orders_7d", 0)),
            device_distinct_buyers_prior=int(row.get("device_distinct_buyers_prior", 0)),
            account_age_days=int(row.get("account_age_days", 0)),
            phone_verified=int(row.get("phone_verified", 0)),
            risk_score=float(risk_score),
            anomaly_score=float(anomaly_score),
            device_id=row.get("device_id"),
        )


def _address_quality_label(completeness: float) -> str:
    if completeness >= 0.75:
        return "good"
    if completeness >= 0.4:
        return "partial"
    return "poor"


def get_buyer_history(ctx: OrderContext) -> dict:
    return {
        "prior_orders": ctx.buyer_prior_orders,
        "prior_rto_rate": round(ctx.buyer_prior_rto, 3),
        "first_time_buyer": bool(ctx.is_first_time_buyer),
        "account_age_days": ctx.account_age_days,
    }


def check_address(ctx: OrderContext) -> dict:
    return {
        "completeness": round(ctx.address_completeness, 3),
        "quality": _address_quality_label(ctx.address_completeness),
        "serviceable": bool(ctx.is_serviceable),
    }


def get_pincode_risk(ctx: OrderContext) -> dict:
    return {
        "pincode": ctx.pincode,
        "historical_rto_rate": round(ctx.pincode_rto_rate, 3),
        "city_tier": ctx.city_tier,
    }


def check_velocity(ctx: OrderContext) -> dict:
    ring = ctx.device_distinct_buyers_prior >= 3 or ctx.device_orders_24h >= 5
    return {
        "device_orders_24h": ctx.device_orders_24h,
        "buyer_orders_7d": ctx.buyer_orders_7d,
        "distinct_buyers_on_device": ctx.device_distinct_buyers_prior,
        "ring_suspected": bool(ring),
    }


# Registry the agent plans over.
TOOLS = {
    "get_buyer_history": get_buyer_history,
    "check_address": check_address,
    "get_pincode_risk": get_pincode_risk,
    "check_velocity": check_velocity,
}
