"""Grounded analyst copilot for Axiom.

A read-only Q&A layer over a single case. It answers *only* from the material actually on
file — the order facts, the model's score, the SHAP risk drivers, the current recommendation,
and the policy clauses retrieved for the question. The system prompt forbids invention and
requires an explicit "that isn't in the record" when the answer isn't grounded. This keeps the
copilot on the right side of the faithfulness-vs-plausibility line: it explains and cites, it
never free-roams. Defense-only — it helps a reviewer understand and act, nothing more.
"""
from __future__ import annotations

import json

from src.agent.llm import LLMError, LLMProvider

COPILOT_SYSTEM = (
    "You are Axiom's analyst copilot for a single cash-on-delivery order under review in India. "
    "Answer the reviewer's question USING ONLY the case file provided (order facts, model score, "
    "SHAP risk drivers, current recommendation, and retrieved policy). Do NOT invent facts, "
    "numbers, or history that are not in the case file. If the answer is not in the record, say "
    "so plainly (e.g. 'That isn't in the case record.'). You may reason about policy consequences "
    "of the facts on file (for example, what a successful step-up verification would satisfy), but "
    "clearly mark that as conditional. Cite policy clause ids you rely on. Be concise (2-4 "
    "sentences) and strictly defensive — never advise how to evade or defeat controls. "
    'Respond as JSON: {"answer": "...", "policy_citations": ["ID", ...]}.'
)

COPILOT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "policy_citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "policy_citations"],
}


def build_context(*, order: dict, risk_score: float, anomaly_score: float, band: str,
                  decision: dict, factors: list[dict], policy: list[str]) -> str:
    """Render the ONLY facts the copilot is allowed to use into a compact case file."""
    def g(key, default="?"):
        return order.get(key, default)

    lines = [
        "CASE FILE (the only facts you may use):",
        f"Order {decision.get('order_id', g('order_id'))} — {g('payment_method')}, "
        f"₹{float(g('order_value', 0)):.0f}, {g('city')} (tier {g('city_tier')}), "
        f"pincode {g('pincode')}.",
        f"Address completeness {float(g('address_completeness', 0)) * 100:.0f}%. "
        f"Account age {g('account_age_days')}d, first-time buyer: "
        f"{'yes' if int(g('is_first_time_buyer', 0)) else 'no'}, "
        f"phone verified: {'yes' if int(g('phone_verified', 0)) else 'no'}.",
        f"Model: RTO risk {risk_score:.2f} ({band} band), anomaly {anomaly_score:.2f}.",
        f"Current recommendation: {decision.get('action')} — \"{decision.get('reason', '')}\" "
        f"(policy: {', '.join(decision.get('policy_citations', [])) or 'n/a'}).",
    ]
    if factors:
        drivers = "; ".join(
            f"{f.get('label', f.get('feature'))} {f.get('direction', '')} risk" for f in factors[:5])
        lines.append(f"Top risk drivers (SHAP): {drivers}.")
    if policy:
        lines.append("Relevant policy clauses:")
        lines += [f"  - {s}" for s in policy]
    return "\n".join(lines)


def answer(question: str, *, order: dict, risk_score: float, anomaly_score: float, band: str,
           decision: dict, factors: list[dict], policy: list[str],
           provider: LLMProvider) -> dict:
    """Answer one grounded question about the case. Returns {answer, citations, grounded}."""
    context = build_context(order=order, risk_score=risk_score, anomaly_score=anomaly_score,
                            band=band, decision=decision, factors=factors, policy=policy)
    prompt = f"{context}\n\nReviewer's question: {question}\nAnswer as JSON per the schema."
    try:
        raw = provider.generate(prompt, system=COPILOT_SYSTEM, response_schema=COPILOT_SCHEMA,
                                thinking_budget=0, max_output_tokens=320, temperature=0.0)
        data = json.loads(raw)
        text = str(data.get("answer", "")).strip()
        if not text:
            raise ValueError("empty answer")
        # Keep only citations that were actually offered to the model (no invented ids).
        offered = " ".join(policy) + " " + " ".join(decision.get("policy_citations", []))
        cites = [c for c in data.get("policy_citations", []) if isinstance(c, str) and c in offered]
        return {"answer": text, "citations": cites, "grounded": True}
    except (LLMError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return {"answer": "The copilot is unavailable right now — please rely on the case file "
                          "and policy citations above.", "citations": [], "grounded": False}
