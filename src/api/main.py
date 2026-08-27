"""FastAPI service for Axiom — the backend the dashboard calls.

Endpoints (all read the held-out test split as the live order queue):
    GET  /                              health
    GET  /orders?limit=                 the risk queue (fast core decisions)
    GET  /orders/{id}                   full case detail (score + SHAP + decision)
    POST /orders/{id}/investigate       run the bounded agent (LLM), persist to audit
    POST /orders/{id}/ask               grounded analyst copilot (Q&A over the case + policy)
    POST /batch/run                     autonomous batch over the amber queue (honest ₹ recovered)
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


class ExecuteBody(BaseModel):
    action: str | None = None


class AskBody(BaseModel):
    question: str


class BatchBody(BaseModel):
    max_orders: int | None = None
    budget_calls: int | None = None
    stop_after_low_value: int | None = None
    low_value_threshold: float | None = None
    quiet_hours: tuple[int, int] | None = None
    scan_limit: int | None = None
    now_hour: int | None = None  # override local hour (demo); else the server clock is used


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


@app.post("/orders/{order_id}/ask")
def order_ask(order_id: str, body: AskBody) -> dict:
    try:
        return get_engine().ask(order_id, body.question)
    except KeyError:
        raise HTTPException(status_code=404, detail="order not found")


@app.post("/orders/{order_id}/execute")
def execute(order_id: str, body: ExecuteBody) -> dict:
    try:
        return get_engine().execute(order_id, body.action)
    except KeyError:
        raise HTTPException(status_code=404, detail="order not found")


@app.post("/batch/run")
def batch_run(body: BatchBody | None = None) -> dict:
    import datetime

    from src.agent.batch import BatchConfig

    body = body or BatchBody()
    d = BatchConfig()
    cfg = BatchConfig(
        max_orders=body.max_orders or d.max_orders,
        budget_calls=body.budget_calls or d.budget_calls,
        stop_after_low_value=body.stop_after_low_value or d.stop_after_low_value,
        low_value_threshold=body.low_value_threshold or d.low_value_threshold,
        quiet_hours=body.quiet_hours if body.quiet_hours is not None else d.quiet_hours,
    )
    now_hour = body.now_hour if body.now_hour is not None else datetime.datetime.now().hour
    return get_engine().run_batch(cfg, now_hour=now_hour, scan_limit=body.scan_limit)


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


@app.get("/leakage")
def leakage() -> dict:
    return get_engine().leakage_report()


@app.get("/rings")
def rings() -> dict:
    return get_engine().rings()


@app.get("/rings/{ring_id}")
def ring_graph(ring_id: str) -> dict:
    try:
        return get_engine().ring_graph(ring_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="ring not found")
