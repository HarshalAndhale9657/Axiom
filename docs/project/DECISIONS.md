# Decision Log (ADR-lite)

One entry per real choice: the decision, the rationale, and when to revisit. Newest first.

## 2026-08-28 — Provider fail-over (Gemini→OpenAI) + honesty-tracked verifier independence
**Decision:** Add a `FallbackProvider` and an `AXIOM_LLM_PROVIDER=auto` mode that tries **Gemini (free) first and fails over to OpenAI `gpt-4o-mini` on 429/quota exhaustion**. The cross-vendor verifier (C2) now records *which vendor actually served* the primary decision and only claims "independent" when the two vendors genuinely differ; a fail-over that makes both OpenAI is labelled "second-pass (same vendor)".
**Why:** Autonomous batch mode fires the LLM many times in seconds and reliably trips Gemini's free-tier daily quota (observed HTTP 429). Graceful degradation to the deterministic core is honest but makes the flagship "agent" demo look rule-driven. Failing over to the already-provisioned OpenAI budget (~$0.001/batch) keeps the agent genuinely reasoning, while the vendor-tracking keeps the C2 independence claim truthful (the honesty rubric explicitly forbids overclaiming cross-vendor independence).
**Revisit if:** we get higher Gemini quota or Anthropic credits — then make Claude the primary and Gemini/OpenAI the fallbacks; independence logic is already vendor-agnostic.

## 2026-08-28 — Batch ₹-recovered reported as an honest 2×2 net, not a headline gross
**Decision:** Autonomous batch mode reports **gross recovered − friction cost on genuine customers = net**, plus RTOs missed, all measured post-hoc on the labelled held-out test batch, with the modelling assumption ("an applied friction prevents that return") stated in the payload and UI.
**Why:** A gross "₹ recovered" number alone is exactly the cherry-pick Track 2 penalizes. Showing the friction cost we impose on good customers (the false-positive side) is the same BMR discipline as the cost curve, and it's more persuasive precisely because it's not hiding the downside.
**Revisit if:** we add per-action recovery factors (e.g. part-pay only de-risks the deposit) — keep the assumption line in sync.

## 2026-08-26 — Scope, product, and track
**Decision:** Compete in **Track 2 (AI Risk Manager)**; focus on **RTO/COD fraud** (over card fraud or "both rails"); product name **Axiom**.
**Why:** RTO/COD is Razorpay's most-talked-about India problem (Thirdwatch/RTO Shield), has the cleanest false-positive-cost story, and the best leakage-safe data path. Axiom = "a self-evident truth" — fits our honest-metrics edge; backronym: Agentic, eXplainable Intelligence for Order-risk Management; tagline "Risk decisions you can prove."
**Revisit if:** the form reveals a constraint that rules out RTO, or a teammate joins (then consider the second payment-fraud rail).

## 2026-08-26 — LightGBM is the primary model; GNN & DP-SGD are stretch, NOT core
**Decision:** Core detector = calibrated **LightGBM** (+ IsolationForest anomaly layer). Heterogeneous GNN/Transformer (TRUST) and DP-SGD (Opacus) are **stretch demos**.
**Why:** Solo + ~10 days. The evaluation *is* the grade; a rigorously-evaluated LightGBM beats a fancy model evaluated poorly. Full HGNN+Transformer is an overscope risk; DP-SGD needs a neural net and degrades accuracy.
**Revisit if:** core is done, rehearsed, and there's real slack — then add the graph-sequential and/or DP demo.

## 2026-08-26 — "Defense-only" ≠ "must use differential privacy"
**Decision:** Treat defense-only as *no offense-capable tooling* (which we inherently satisfy). DP is a bonus, not a requirement, and stays off the primary model.
**Why:** The user's research PDF framed DP-SGD as mandatory for defense-only; that over-interprets the rubric. Overclaiming it would be dishonest on a track that grades honesty.

## 2026-08-26 — LLM layer runs on FREE tiers, provider-agnostic
**Decision:** Build the reason-code + agent layer behind an `LLMProvider` interface; default to **Gemini free tier** (no card needed); Groq/local Ollama as fallbacks; reserve OpenAI ~$2.44 for the final demo.
**Why:** No Anthropic key available (can't purchase). The core ML + eval (the grade) is 100% local/free. Provider-agnostic is also a *strength* ("architected for Claude Agent SDK — Razorpay's stack — demoed on free tier").
**Revisit if:** the buildathon grants Anthropic/AWS credits — then run on Claude for full alignment.

## 2026-08-26 — Primary data = synthetic COD generator + real pincode grounding
**Decision:** Build a controllable **synthetic COD order generator** (causal RTO model) grounded in the real All-India pincode directory. IEEE-CIS is only for the stretch payment-fraud rail; Olist for optional real-data validation.
**Why:** No clean public Indian COD-RTO labeled set exists. A causal generator gives ground truth → honest metrics with **no leakage**. IEEE-CIS is card fraud, not RTO. We disclose synthetic data openly.

## 2026-08-26 — Leakage discipline as core methodology
**Decision:** Time-based split; out-of-fold/training-only encoding for pincode & buyer-history features; resampling only inside CV folds; calibrated probabilities.
**Why:** Public RTO models online report ~0.99 AUC that almost certainly leaks the label. Out-honesting them *is* our differentiator and the literal "honest metrics" bar.

## 2026-08-26 — Evaluation framed as Bayes Minimum Risk (BMR / Elkan)
**Decision:** Name the cost-vs-threshold analysis "Bayes Minimum Risk," cite Elkan, report the rupee-denominated confusion matrix, τ\*, PR-AUC, precision@k, and a failure-mode matrix.
**Why:** Same math we planned, but the formal framing signals real ML-evaluation discipline (merged from the user's research PDF).

## 2026-08-26 — UI = Next.js dashboard, Streamlit fallback
**Decision:** Build a polished Next.js + Tailwind dashboard (Claude scaffolds it); keep Streamlit as a documented Plan B.
**Why:** The demo is the single biggest driver of outcome; a real-looking product matters. But web isn't the user's strength, so a Streamlit fallback de-risks it.
**Revisit if:** web debugging eats >1.5 days → switch to Streamlit.
