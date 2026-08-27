"""FastAPI service for Axiom — the backend the dashboard calls.

Endpoints (all read the held-out test split as the live order queue):
    GET  /                              health
    GET  /orders?limit=                 the risk queue (fast core decisions)
    GET  /orders/{id}                   full case detail (score + SHAP + decision)
    POST /orders/{id}/investigate       run the bounded agent (LLM), persist to audit
    POST /decisions/{id}/override       human-in-the-loop override (immutable)
    GET  /audit?limit=                  the immutable audit trail
    GET  /metrics                       honest BMR cost-story numbers
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.service import RiskEngine

app = FastAPI(title="Axiom — AI Risk Manager", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

_engine: RiskEngine | None = None


def get_engine() -> RiskEngine:
    global _engine
    if _engine is None:
        _engine = RiskEngine()  # loaded once, lazily, on first request
    return _engine


class OverrideBody(BaseModel):
    reviewer: str
    to_action: str
    reason: str


@app.get("/")
def health() -> dict:
    return {"service": "axiom", "status": "ok"}


@app.get("/orders")
def orders(limit: int = 50) -> list[dict]:
    return get_engine().queue_view(limit)


@app.get("/orders/{order_id}")
def order_detail(order_id: str) -> dict:
    try:
        return get_engine().assess(order_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="order not found")


@app.post("/orders/{order_id}/investigate")
def order_investigate(order_id: str) -> dict:
    try:
        return get_engine().investigate(order_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="order not found")


@app.post("/decisions/{decision_id}/override")
def override(decision_id: int, body: OverrideBody) -> dict:
    try:
        return get_engine().override(decision_id, body.reviewer, body.to_action, body.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="decision not found")


@app.get("/audit")
def audit(limit: int = 100) -> list[dict]:
    return get_engine().audit_log(limit)


@app.get("/metrics")
def metrics() -> dict:
    return get_engine().metrics()


@app.get("/costcurve")
def costcurve() -> dict:
    return get_engine().cost_curve_points()
