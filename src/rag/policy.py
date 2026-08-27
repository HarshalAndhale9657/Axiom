"""Policy RAG for Axiom — retrieve the relevant risk-policy clauses.

Lightweight and offline: TF-IDF cosine similarity over the policy clauses (scikit-learn,
already a dependency) — no torch, no vector DB, no network, $0. The policy document
(``docs/policy/rto_cod_risk_policy.md``) is the single source of truth; every clause keeps
its ``RTO-POL-*`` id so the agent can cite it and the audit trail can verify the citation.
Swappable for ChromaDB/embeddings later behind the same ``retrieve`` interface.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

DEFAULT_POLICY = "docs/policy/rto_cod_risk_policy.md"
_CLAUSE_RE = re.compile(r"RTO-POL-[\d.]+")


@dataclass(frozen=True)
class Clause:
    clause_id: str
    text: str


def parse_policy(path: str | Path = DEFAULT_POLICY) -> list[Clause]:
    """Split the policy markdown into one retrievable chunk per ``RTO-POL-*`` line."""
    clauses: list[Clause] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        match = _CLAUSE_RE.search(stripped)
        if not match:
            continue
        text = re.sub(r"[#*`>]", " ", stripped)          # drop markdown noise
        text = re.sub(r"^[\s\-]+", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        clauses.append(Clause(match.group(0), text))
    return clauses


class PolicyRetriever:
    """TF-IDF retriever over policy clauses."""

    def __init__(self, clauses: list[Clause] | None = None,
                 path: str | Path = DEFAULT_POLICY) -> None:
        self.clauses = clauses if clauses is not None else parse_policy(path)
        if not self.clauses:
            raise ValueError("no policy clauses parsed — check the policy document path")
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform([c.text for c in self.clauses])

    def retrieve(self, query: str, k: int = 3) -> list[tuple[str, str, float]]:
        """Return the top-``k`` (clause_id, text, similarity) for a query, most-similar first."""
        q = self.vectorizer.transform([query])
        sims = linear_kernel(q, self.matrix).ravel()
        order = sims.argsort()[::-1][:k]
        return [(self.clauses[i].clause_id, self.clauses[i].text, float(sims[i]))
                for i in order if sims[i] > 0]

    def snippets(self, query: str, k: int = 3) -> list[str]:
        """Retrieval formatted as ``'RTO-POL-x.y: <text>'`` strings for prompts/citations."""
        return [f"{cid}: {text}" for cid, text, _ in self.retrieve(query, k)]
