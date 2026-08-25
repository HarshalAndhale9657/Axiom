# Goals — What We Want

## North star
Get selected as a **Razorpay AI Builder Intern** by submitting a Track-2 project with undeniable *"signal"* — a working, honest, industry-grade AI Risk Manager that a payments company could actually trust near real money.

## The product (one line)
**Axiom** — an AI Risk Manager for COD/RTO fraud: a calibrated ML detector + SHAP-grounded LLM explanations + a bounded agentic investigator + human-in-the-loop audit trail, evaluated with an honest rupee cost-vs-threshold curve.

## Success criteria (our Definition of Done — full list in [PLAN.md](../../PLAN.md))
- Public repo, **one-command run**, seed data included.
- **Detector + verifier + auto-responder** all demonstrably present (covers all 3 Track-2 modalities).
- Evaluation: PR-AUC vs baseline, precision@k, calibration, **BMR rupee cost-vs-threshold curve with τ\***, explicit **leakage-avoidance** statement, **failure-mode matrix**.
- Meaningful AI: LLM reason codes (grounded), a bounded agent with policy RAG + structured decisions, HITL + immutable audit.
- **Defense-only** stated and true. Every claim honest; at least one stated limitation.
- A rehearsed 5-minute pitch video + a fallback recording.

## Why this wins (our two edges the field will miss)
1. **Alignment** — mirrors Razorpay's own stack (Thirdwatch/RTO Shield, Bumblebee multi-agent, rules-before-LLM, Good/Bad/Grey tiering).
2. **Honesty as a feature** — leakage-safe eval + false-positive cost is the literal rubric, and we make it the headline.

## Non-goals (what we will NOT do)
- ❌ Anything offense-capable (evasion tooling, fraud generation) — instant DQ and against our values.
- ❌ Overscoping: no Kafka/Flink, no full HGNN+Transformer as the core, no DP-SGD replacing LightGBM. These are *stretch demos* only.
- ❌ Chasing model complexity for its own sake — the eval and the story win, not the fanciest architecture.
- ❌ Paid APIs — we build on free tiers.
