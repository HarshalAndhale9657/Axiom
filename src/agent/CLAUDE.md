# Agent — bounded, grounded, defense-only

This is the LLM investigation layer. Rules that must hold:

- **Provider-agnostic.** All model calls go through the `LLMProvider` interface. Default = Gemini (free). Never hardcode a vendor or an API key; read from `.env`. Never call a paid API in tests — mock it.
- **Bounded action space only:** `approve · step_up_verification · part_pay_cod · convert_cod_to_prepaid · hold_for_review · escalate_to_human`. The agent can emit nothing else. Enforce with a Pydantic schema + a test.
- **The LLM never overrides the ML score.** It explains, investigates, and recommends *within* policy. Deterministic rules run first.
- **Grounded explanations only.** Reason codes may cite *only* the provided SHAP factors + retrieved policy text. No invented reasons (avoids the faithfulness-vs-plausibility trap).
- **Every tool call and decision is logged** to the audit trail (input, tools, citations, action, confidence, any human override).
- **Defense-only.** The agent investigates and protects; it never generates fraud or evasion guidance.
- Only the **AMBER** band reaches the agent (green/red are handled deterministically) — keeps cost bounded.

See [../../docs/policy/rto_cod_risk_policy.md](../../docs/policy/rto_cod_risk_policy.md) and [PLAN.md §8](../../PLAN.md).
