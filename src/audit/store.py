"""Immutable audit trail for Axiom (SQLite, dependency-free stdlib).

Every automated decision and every human override is recorded. Immutability is enforced at
the database level: ``BEFORE UPDATE``/``BEFORE DELETE`` triggers abort any attempt to alter
or remove a logged decision or override — so the trail is genuinely append-only, which is
exactly what an auditor / regulator expects of a high-risk AI system.

A human override never edits the original decision; it is a new ``overrides`` row that
references it, preserving the full before/after chain.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    ts REAL NOT NULL,
    risk_score REAL, anomaly_score REAL,
    band TEXT, action TEXT, reason TEXT,
    confidence REAL, requires_human INTEGER,
    source TEXT, model_version TEXT,
    detail TEXT
);
CREATE TABLE IF NOT EXISTS overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id INTEGER NOT NULL,
    ts REAL NOT NULL,
    reviewer TEXT, from_action TEXT, to_action TEXT, reason TEXT,
    FOREIGN KEY (decision_id) REFERENCES decisions(id)
);
CREATE TRIGGER IF NOT EXISTS decisions_no_update BEFORE UPDATE ON decisions
    BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS decisions_no_delete BEFORE DELETE ON decisions
    BEGIN SELECT RAISE(ABORT, 'decisions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS overrides_no_update BEFORE UPDATE ON overrides
    BEGIN SELECT RAISE(ABORT, 'overrides are append-only'); END;
CREATE TRIGGER IF NOT EXISTS overrides_no_delete BEFORE DELETE ON overrides
    BEGIN SELECT RAISE(ABORT, 'overrides are append-only'); END;
"""


class AuditStore:
    def __init__(self, path: str | Path = "audit.sqlite") -> None:
        self.path = str(path)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    # ---- writes (append-only) -------------------------------------------------------
    def log_decision(self, *, order_id: str, risk_score: float, anomaly_score: float,
                     band: str, action: str, reason: str, confidence: float,
                     requires_human: bool, source: str, model_version: str = "",
                     detail: dict | None = None, ts: float | None = None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO decisions (order_id, ts, risk_score, anomaly_score, band, action,"
                " reason, confidence, requires_human, source, model_version, detail)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (order_id, ts if ts is not None else time.time(), risk_score, anomaly_score,
                 band, action, reason, confidence, int(requires_human), source, model_version,
                 json.dumps(detail or {})),
            )
            return int(cur.lastrowid)

    def log_override(self, *, decision_id: int, reviewer: str, from_action: str,
                     to_action: str, reason: str, ts: float | None = None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO overrides (decision_id, ts, reviewer, from_action, to_action, reason)"
                " VALUES (?,?,?,?,?,?)",
                (decision_id, ts if ts is not None else time.time(), reviewer, from_action,
                 to_action, reason),
            )
            return int(cur.lastrowid)

    # ---- reads ----------------------------------------------------------------------
    def _row_to_decision(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["requires_human"] = bool(d["requires_human"])
        d["detail"] = json.loads(d["detail"]) if d.get("detail") else {}
        return d

    def get_decision(self, decision_id: int) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
        return self._row_to_decision(row) if row else None

    def get_overrides(self, decision_id: int) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM overrides WHERE decision_id=? ORDER BY id",
                             (decision_id,)).fetchall()
        return [dict(r) for r in rows]

    def list_decisions(self, limit: int = 100) -> list[dict]:
        """Most-recent decisions, each with its override chain attached."""
        with self._conn() as c:
            rows = c.execute("SELECT * FROM decisions ORDER BY id DESC LIMIT ?",
                             (limit,)).fetchall()
        out = []
        for r in rows:
            d = self._row_to_decision(r)
            d["overrides"] = self.get_overrides(d["id"])
            out.append(d)
        return out
