"""Tests for the policy RAG retriever."""
from __future__ import annotations

import pytest

from src.rag.policy import PolicyRetriever, parse_policy


@pytest.fixture(scope="module")
def retriever() -> PolicyRetriever:
    return PolicyRetriever()


def test_policy_parses_into_clauses():
    clauses = parse_policy()
    assert len(clauses) >= 8
    assert all(c.clause_id.startswith("RTO-POL-") for c in clauses)


def test_retrieves_relevant_clause_for_nonserviceable(retriever):
    ids = [cid for cid, _, _ in retriever.retrieve("delivery pincode non-serviceable undeliverable", 3)]
    assert "RTO-POL-2.2" in ids


def test_retrieves_relevant_clause_for_trusted_repeat_buyer(retriever):
    ids = [cid for cid, _, _ in retriever.retrieve("trusted repeat buyer prepaid auto approve", 3)]
    assert "RTO-POL-2.1" in ids


def test_snippets_are_cited_strings(retriever):
    snips = retriever.snippets("amber step-up verification prepaid nudge", 3)
    assert snips and all(s.startswith("RTO-POL-") for s in snips)
