"""Bounded investigation agent for Axiom (AMBER band only).

Mirrors Razorpay's Bumblebee shape: a **planner** picks which typed tools to run, the tools
gather evidence (each recorded for the audit trail), policy is retrieved via **RAG**, and the
LLM emits a **schema-constrained structured decision** — validated against the closed action
set, with a **deterministic fallback** so we ALWAYS return a bounded, auditable recommendation.

Guardrails (defense-only, bounded, auditable):
* Hard rules already ran in the decision core; the agent only investigates the AMBER band.
* The LLM can only choose an action from a fixed enum; anything else -> deterministic fallback.
* The LLM sees only tool evidence + retrieved policy; the system prompt forbids invention.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from src.agent.llm import LLMError, LLMProvider, get_provider
from src.agent.tools import TOOLS, OrderContext
from src.rag.policy import PolicyRetriever
from src.rules.decision_core import ACTIONS, DecisionConfig, decide

# Actions appropriate for a borderline (amber) case — dynamic friction, not hard blocks.
AMBER_ACTIONS = ["approve", "step_up_verification", "part_pay_cod",
                 "convert_cod_to_prepaid", "escalate_to_human"]

AGENT_SYSTEM = (
    "You are Axiom's investigation agent for BORDERLINE (amber) cash-on-delivery orders in "
    "India. Given tool evidence and retrieved policy, recommend exactly ONE action. Base the "
    "recommendation ONLY on the provided evidence and cited policy — never invent facts. "
    "Prefer dynamic friction (verify / part-pay / convert to prepaid) over hard blocks: the "
    "false-positive cost of blocking a genuine customer is high. Escalate to a human only when "
    "the case is genuinely ambiguous or high-value. You are strictly defensive."
)

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": AMBER_ACTIONS},
        "confidence": {"type": "number"},
        "requires_human": {"type": "boolean"},
        "rationale": {"type": "string"},
        "policy_citations": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action", "confidence", "requires_human", "rationale", "policy_citations"],
}


@dataclass
class ToolCall:
    name: str
    output: dict

    def as_dict(self) -> dict:
        return {"tool": self.name, "output": self.output}


@dataclass
class AgentDecision:
    action: str
    confidence: float
    rationale: str
    requires_human: bool
    policy_citations: list[str]
    evidence: list[ToolCall]
    retrieved_policy: list[str]
    source: str  # "llm" | "fallback"
    verification: dict | None = None  # independent cross-vendor verdict, if any

    def as_dict(self) -> dict:
        return {
            "action": self.action, "confidence": round(self.confidence, 3),
            "rationale": self.rationale, "requires_human": self.requires_human,
            "policy_citations": self.policy_citations,
            "evidence": [c.as_dict() for c in self.evidence],
            "retrieved_policy": self.retrieved_policy, "source": self.source,
            "verification": self.verification,
        }


def plan_tools(ctx: OrderContext) -> list[str]:
    """Pick which tools to run — skip velocity for a brand-new device/buyer with no history."""
    plan = ["check_address", "get_pincode_risk", "get_buyer_history"]
    if ctx.device_orders_24h > 0 or ctx.device_distinct_buyers_prior > 0 \
            or not ctx.is_first_time_buyer:
        plan.append("check_velocity")
    return plan


def _policy_query(ctx: OrderContext) -> str:
    pay = "COD" if ctx.is_cod else "prepaid"
    return (f"{pay} amber borderline order step-up verification part-pay convert prepaid "
            f"address quality pincode RTO risk buyer history escalate")


def _build_prompt(ctx: OrderContext, calls: list[ToolCall], snippets: list[str]) -> str:
    lines = [
        f"Order {ctx.order_id}: model risk_score={ctx.risk_score:.2f} (amber band), "
        f"anomaly={ctx.anomaly_score:.2f}, payment={'COD' if ctx.is_cod else 'prepaid'}, "
        f"order_value=Rs{ctx.order_value:.0f}.",
        "Evidence gathered by tools:",
    ]
    lines += [f"  - {c.name}: {json.dumps(c.output)}" for c in calls]
    lines.append("Relevant policy clauses (cite these ids in policy_citations):")
    lines += [f"  - {s}" for s in snippets]
    lines.append(f"Choose exactly one action from {AMBER_ACTIONS} and return JSON per schema.")
    return "\n".join(lines)


def _fallback(ctx: OrderContext, calls: list[ToolCall], snippets: list[str],
              config: DecisionConfig) -> AgentDecision:
    d = decide(order_id=ctx.order_id, risk_score=ctx.risk_score, is_cod=ctx.is_cod,
               order_value=ctx.order_value, is_serviceable=ctx.is_serviceable,
               device_orders_24h=ctx.device_orders_24h,
               buyer_prior_orders=ctx.buyer_prior_orders, buyer_prior_rto=ctx.buyer_prior_rto,
               anomaly_score=ctx.anomaly_score, device_id=ctx.device_id, config=config)
    return AgentDecision(d.action, d.confidence, d.reason, d.requires_human,
                         d.policy_citations, calls, snippets, "fallback")


def _attach_verification(dec: AgentDecision, ctx: OrderContext, verifier,
                         primary_provider: LLMProvider | None = None) -> None:
    """Run the cross-vendor verifier and attach its verdict (veto -> human).

    Honesty: we compare the vendor that actually served the primary decision against the
    verifier's vendor and mark ``independent`` accordingly — so we never claim cross-vendor
    independence when a fail-over made both the same vendor.
    """
    from src.agent.llm import provider_vendor
    from src.agent.verify import get_verifier, verifier_vendor_key, verify_decision

    if verifier == "auto":
        prov, label = get_verifier()
        v_vendor = verifier_vendor_key()
    elif verifier is None:
        prov, label = None, None
        v_vendor = "none"
    else:
        prov, label = verifier, "verifier"
        v_vendor = provider_vendor(verifier)
    if prov is None:
        return
    verdict = verify_decision(dec, ctx, provider=prov, vendor_label=label)
    if verdict:
        p_vendor = provider_vendor(primary_provider) if primary_provider is not None else "unknown"
        verdict["independent"] = bool(p_vendor not in (v_vendor, "unknown"))
        dec.verification = verdict
        if verdict["verdict"] == "veto":
            dec.requires_human = True


def investigate(ctx: OrderContext, retriever: PolicyRetriever, *,
                provider: LLMProvider | None = None,
                config: DecisionConfig | None = None, verifier="auto") -> AgentDecision:
    """Run the bounded investigation, verify it independently, and return the recommendation."""
    config = config or DecisionConfig()
    calls = [ToolCall(name, TOOLS[name](ctx)) for name in plan_tools(ctx)]
    snippets = retriever.snippets(_policy_query(ctx), k=4)
    prov = provider or get_provider()
    prompt = _build_prompt(ctx, calls, snippets)
    try:
        raw = prov.generate(prompt, system=AGENT_SYSTEM, response_schema=DECISION_SCHEMA,
                            thinking_budget=0, max_output_tokens=400, temperature=0.0)
        data = json.loads(raw)
        action = data.get("action")
        if action not in ACTIONS:                     # bound-check the LLM's choice
            dec = _fallback(ctx, calls, snippets, config)
        else:
            confidence = min(max(float(data.get("confidence", 0.6)), 0.0), 1.0)
            citations = [c for c in data.get("policy_citations", []) if isinstance(c, str)]
            dec = AgentDecision(action, confidence, str(data.get("rationale", "")).strip(),
                                bool(data.get("requires_human", False)), citations,
                                calls, snippets, "llm")
    except (LLMError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        dec = _fallback(ctx, calls, snippets, config)
    _attach_verification(dec, ctx, verifier, primary_provider=prov)
    return dec
