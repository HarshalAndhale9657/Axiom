"""Tests for autonomous batch mode — stopping rules, honest ₹ math, and audit coverage."""
from __future__ import annotations

import json

import pytest

from src.agent.batch import (BatchConfig, BatchState, in_quiet_hours, is_intervention,
                             recovered_and_cost, stop_reason, update_state)
from src.agent.llm import MockProvider
from src.api.service import RiskEngine
from src.data.generate_synthetic_cod import generate

VALID_AGENT_JSON = json.dumps({
    "action": "step_up_verification", "confidence": 0.7, "requires_human": False,
    "rationale": "Borderline COD; verify before dispatch.", "policy_citations": ["RTO-POL-3.2"],
})


# ---- pure helpers ---------------------------------------------------------------------
def test_intervention_classification():
    assert is_intervention("step_up_verification")
    assert is_intervention("convert_cod_to_prepaid")
    assert not is_intervention("approve")


def test_quiet_hours_same_day_and_overnight():
    assert in_quiet_hours(23, (22, 6)) and in_quiet_hours(3, (22, 6))   # overnight wrap
    assert not in_quiet_hours(12, (22, 6))
    assert in_quiet_hours(14, (9, 17)) and not in_quiet_hours(8, (9, 17))  # same-day window
    assert not in_quiet_hours(5, None) and not in_quiet_hours(None, (22, 6))  # disabled / no clock


def test_recovered_and_cost_branches():
    # intervention on a would-be RTO -> recover c_fn, no friction cost
    assert recovered_and_cost("step_up_verification", 1, 500.0, 90.0) == (500.0, 0.0)
    # intervention on a genuine customer -> incur the friction cost (honest downside)
    assert recovered_and_cost("convert_cod_to_prepaid", 0, 500.0, 90.0) == (0.0, 90.0)
    # a clean approve has no rupee effect in the recovery tally
    assert recovered_and_cost("approve", 1, 500.0, 90.0) == (0.0, 0.0)


def test_stop_rules_each_fire():
    assert stop_reason(BatchState(processed=3), BatchConfig(max_orders=3)).startswith("reached max")
    assert "call budget" in stop_reason(BatchState(calls=2), BatchConfig(budget_calls=2))
    cfg = BatchConfig(stop_after_low_value=2)
    assert "consecutive" in stop_reason(BatchState(consecutive_low_value=2), cfg)
    assert stop_reason(BatchState(), BatchConfig()) is None


def test_update_state_low_value_streak_resets():
    cfg = BatchConfig(low_value_threshold=400.0)
    s = BatchState()
    update_state(s, 100.0, cfg)
    update_state(s, 200.0, cfg)
    assert s.consecutive_low_value == 2 and s.processed == 2 and s.calls == 2
    update_state(s, 900.0, cfg)   # a high-value order resets the streak
    assert s.consecutive_low_value == 0 and s.processed == 3


# ---- engine integration ---------------------------------------------------------------
@pytest.fixture(scope="module")
def engine(tmp_path_factory) -> RiskEngine:
    orders, _ = generate(n=5000, seed=0)
    audit = tmp_path_factory.mktemp("audit") / "audit.sqlite"
    return RiskEngine(orders=orders, audit_path=str(audit),
                      provider=MockProvider(canned=VALID_AGENT_JSON), queue_limit=60)


def test_run_batch_processes_amber_and_tallies(engine):
    res = engine.run_batch(BatchConfig(max_orders=8), now_hour=12)
    assert 1 <= res["processed"] <= 8
    assert res["amber_seen"] == res["processed"]              # every amber seen was processed
    assert res["net_recovered"] == res["recovered_gross"] - res["friction_cost"]
    assert res["interventions"] == res["rto_caught"] + res["good_frictioned"]
    assert len(res["actions"]) == res["processed"]
    assert isinstance(res["stop_reason"], str) and res["stop_reason"]
    assert "basis" in res                                     # honesty disclosure present


def test_run_batch_respects_quiet_hours(engine):
    res = engine.run_batch(BatchConfig(quiet_hours=(22, 6)), now_hour=23)
    assert res["processed"] == 0 and "quiet hours" in res["stop_reason"]


def test_batch_decisions_are_audited_with_batch_source(engine):
    res = engine.run_batch(BatchConfig(max_orders=3), now_hour=12)
    ids = {a["decision_id"] for a in res["actions"]}
    logged = {d["id"]: d for d in engine.audit_log(limit=60)}
    assert ids and ids.issubset(logged)
    assert all(logged[i]["source"].startswith("batch:") for i in ids)
