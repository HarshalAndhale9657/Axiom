"""Grounded LLM reason codes for Axiom.

The model decides; SHAP says *why*; the LLM only **phrases** what SHAP already found. The
prompt contains ONLY the provided factors + retrieved policy, and the system instruction
forbids inventing anything — our explicit mitigation for the documented
faithfulness-vs-plausibility gap (a persuasive but unfaithful explanation is worse than a
plain one). If the LLM is unavailable, we fall back to the deterministic SHAP reason, so
the system never blocks on the network or a key.
"""
from __future__ import annotations

from src.agent.llm import LLMError, LLMProvider, get_provider
from src.model.explain import Explanation

SYSTEM = (
    "You are Axiom, a defensive COD/RTO risk assistant for a payments company. "
    "Write ONE concise sentence (<=30 words) that a fraud analyst can read, explaining the "
    "recommendation. Use ONLY the factors and policy provided below. Do NOT invent numbers, "
    "features, customer details, or reasons that are not listed. Neutral, professional tone."
)


def build_prompt(order_id: str, risk_score: float, band: str, action: str,
                 factors: list[dict], policy_snippets: list[str]) -> str:
    """Assemble a fully-grounded prompt (only provided facts appear)."""
    lines = [
        f"Order {order_id}: risk_score={risk_score:.2f}, band={band}, "
        f"recommended_action={action}.",
        "Top contributing factors (each: plain label -> direction of effect on RTO risk):",
    ]
    lines += [f"  - {f['label']} -> {f['direction']} risk" for f in factors]
    if policy_snippets:
        lines.append("Relevant policy clauses:")
        lines += [f"  - {s}" for s in policy_snippets]
    lines.append("Now write the single-sentence analyst reason code.")
    return "\n".join(lines)


def generate_reason_code(explanation: Explanation, *, order_id: str, risk_score: float,
                         band: str, action: str, policy_snippets: list[str] | None = None,
                         provider: LLMProvider | None = None) -> str:
    """Grounded one-sentence reason; deterministic SHAP fallback on any LLM failure."""
    factors = explanation.as_payload()
    prompt = build_prompt(order_id, risk_score, band, action, factors, policy_snippets or [])
    prov = provider or get_provider()
    try:
        text = prov.generate(prompt, system=SYSTEM, temperature=0.0, max_output_tokens=200,
                             thinking_budget=0)
        text = " ".join(text.split()).strip().strip('"')
        return text or explanation.grounded_reason()
    except LLMError:
        return explanation.grounded_reason()
