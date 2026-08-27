"""Cross-vendor adversarial verifier for Axiom.

An INDEPENDENT model (by default OpenAI ``gpt-4o-mini`` — a *different vendor* than the
Gemini primary) second-checks the agent's recommended action against the same evidence and
policy, and returns agree / veto. A veto flags the case for a human. This is genuine
multi-agent, multi-vendor rigor — and it's honest: we show which model verified, and if the
verifier runs on the same vendor we say so.
"""
from __future__ import annotations

import json
import os

from src.agent.llm import GeminiProvider, LLMError, LLMProvider, OpenAIProvider
from src.util import load_env

VERIFIER_SYSTEM = (
    "You are an INDEPENDENT risk verifier from a different vendor than the primary agent. "
    "You are given a primary agent's recommended action for a borderline cash-on-delivery "
    "order, plus the evidence and policy it used. Skeptically and independently judge whether "
    "the action is APPROPRIATE and GROUNDED in that evidence + policy. You are strictly "
    "defense-only and prefer dynamic friction over hard blocks. Respond as JSON: "
    '{"verdict": "agree" | "veto", "confidence": 0.0-1.0, "reason": "one short sentence"}.'
)

VERIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["agree", "veto"]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "confidence", "reason"],
}


def get_verifier() -> tuple[LLMProvider | None, str | None]:
    """Return (provider, vendor_label) for an independent verifier, or (None, None) if off."""
    load_env()
    name = os.environ.get("AXIOM_VERIFIER_PROVIDER", "none").lower()
    if name == "openai" and os.environ.get("OPENAI_API_KEY"):
        return OpenAIProvider(), f"{os.environ.get('AXIOM_OPENAI_MODEL', 'gpt-4o-mini')} · OpenAI"
    if name == "gemini":
        return GeminiProvider(), f"{os.environ.get('AXIOM_GEMINI_MODEL', 'gemini')} · Google"
    return None, None


def _prompt(decision, ctx) -> str:
    lines = [
        f"Primary agent reviewed borderline COD order {ctx.order_id} "
        f"(risk {ctx.risk_score:.2f}, value Rs{ctx.order_value:.0f}).",
        f"Recommended action: {decision.action}",
        f"Its rationale: {decision.rationale}",
        "Evidence used:",
    ]
    lines += [f"  - {c.name}: {json.dumps(c.output)}" for c in decision.evidence]
    lines.append("Policy cited:")
    lines += [f"  - {s}" for s in decision.retrieved_policy]
    lines.append("Independently judge whether this action is appropriate and grounded. Return JSON.")
    return "\n".join(lines)


def verify_decision(decision, ctx, *, provider: LLMProvider, vendor_label: str | None = None) -> dict | None:
    """Independent verdict on the primary decision, or None if the verifier fails."""
    try:
        raw = provider.generate(_prompt(decision, ctx), system=VERIFIER_SYSTEM,
                                response_schema=VERIFIER_SCHEMA, temperature=0.0,
                                max_output_tokens=200, thinking_budget=0)
        data = json.loads(raw)
        if data.get("verdict") not in ("agree", "veto"):
            return None
        return {
            "verdict": data["verdict"],
            "confidence": min(max(float(data.get("confidence", 0.6)), 0.0), 1.0),
            "reason": str(data.get("reason", "")).strip(),
            "verifier": vendor_label or "verifier",
        }
    except (LLMError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
