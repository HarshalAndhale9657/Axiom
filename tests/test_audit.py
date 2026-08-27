"""Tests for the immutable audit store."""
from __future__ import annotations

import sqlite3

import pytest

from src.audit.store import AuditStore


@pytest.fixture()
def store(tmp_path) -> AuditStore:
    return AuditStore(tmp_path / "audit.sqlite")


def _log(store: AuditStore, **kw) -> int:
    base = dict(order_id="O1", risk_score=0.3, anomaly_score=0.1, band="amber",
                action="step_up_verification", reason="verify", confidence=0.7,
                requires_human=False, source="llm", model_version="lgbm-test",
                detail={"foo": "bar"})
    base.update(kw)
    return store.log_decision(**base)


def test_log_and_read_decision(store):
    did = _log(store)
    d = store.get_decision(did)
    assert d["order_id"] == "O1" and d["action"] == "step_up_verification"
    assert d["detail"] == {"foo": "bar"} and d["requires_human"] is False


def test_override_chain(store):
    did = _log(store)
    oid = store.log_override(decision_id=did, reviewer="analyst_1",
                             from_action="step_up_verification", to_action="approve",
                             reason="known good customer")
    assert oid > 0
    ov = store.get_overrides(did)
    assert len(ov) == 1 and ov[0]["to_action"] == "approve"
    listed = store.list_decisions()
    assert listed[0]["id"] == did and len(listed[0]["overrides"]) == 1


def test_decisions_are_immutable(store):
    did = _log(store)
    with sqlite3.connect(store.path) as c:
        with pytest.raises(sqlite3.Error):
            c.execute("UPDATE decisions SET action='tampered' WHERE id=?", (did,))
        with pytest.raises(sqlite3.Error):
            c.execute("DELETE FROM decisions WHERE id=?", (did,))
    assert store.get_decision(did)["action"] == "step_up_verification"


def test_persistence_across_reopen(tmp_path):
    path = tmp_path / "audit.sqlite"
    did = _log(AuditStore(path))
    assert AuditStore(path).get_decision(did) is not None
