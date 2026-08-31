# Decision Log (ADR-lite)

One entry per real choice: the decision, the rationale, and when to revisit. Newest first.

## 2026-09-01 — The operating threshold is fitted on validation, never on test
**Decision:** `src/model/threshold.py` fits the rupee-cost-minimising τ on the **validation** split at train time, persists it to `models/thresholds.json`, and the test split is scored exactly once at that frozen value. `report()` still computes the test-optimal threshold but labels it an **oracle** and publishes the gap (the "optimism tax", ₹1,570/1k = 3.1%).
**Why:** The previous evaluation swept the cost curve on test and quoted its `argmin`. That is threshold-selection leakage: the headline was an in-sample optimum unreachable in production, and it was the single most attackable claim in a submission whose entire thesis is honest measurement. Publishing the gap is strictly stronger than hiding it — it demonstrates we knew the shortcut existed and declined it.
**Revisit if:** we move to per-order thresholds (already implemented in `band_cut_points`) — then the frozen artifact becomes the cost/action model rather than two scalars.

## 2026-09-01 — Band cut-points are derived from action economics, not hand-picked
**Decision:** GREEN/AMBER/RED cut-points come from a closed-form solution over each action's friction cost and efficacy (`ActionModel`), replacing the hard-coded 0.15 / 0.45. The efficacies are declared assumptions and are **swept** (`sensitivity()`) rather than asserted.
**Why:** The docs claimed "cost-optimal thresholds" while the code used magic numbers — an overclaim that a judge would find in thirty seconds. The derived pair is also simply better: **₹1,758 per 1,000 orders cheaper** on the test split. The sweep matters more than the point estimate: τ_low ranges 0.11–0.73 across plausible efficacies, so the formula is the deliverable and any merchant must re-derive on their own measured efficacy.
**Revisit if:** we ever obtain real counterfactual data on step-up efficacy — then the assumption becomes a measurement and the sweep collapses.

## 2026-09-01 — Label-derived features respect a 7-day outcome-availability lag
**Decision:** Target encodings only count earlier orders whose RTO outcome had already **resolved** (`outcome_lag_days=7.0`). Velocity and graph counts are unaffected — they count orders, not outcomes.
**Why:** "Use only the past" is not strict enough. An order placed today cannot know whether yesterday's order was returned; the courier has not attempted delivery. The naive as-of encoder was quietly training on knowledge the production scorer will never have at checkout. Cost of the fix: **0.0027 PR-AUC**, measured and published. Finding a leak inside our own leakage-safe pipeline, and paying for it, is worth more than the 0.003 it cost.
**Revisit if:** deployed at a merchant with a known resolution SLA — set the lag from their actual courier data.

## 2026-09-01 — Publish the baseline ablation, including the comparison we lose
**Decision:** `src/model/baselines.py` runs LightGBM against a hand-written expert scorecard and a logistic regression on identical terms (same features, same splits, isotonic calibration on val, each with its own val-fitted threshold), with **paired** bootstrap intervals on the gap. Result: LightGBM clearly beats the scorecard (+0.032 to +0.077 PR-AUC) but the interval against logistic regression **spans zero**. We say so, in the README, the docs, the notebook and the dashboard.
**Why:** "Our model beats doing nothing" is not evidence. The first question an ML panel asks is whether the complexity earned its place. Reporting a null result costs a bragging point and buys the credibility that every *other* number on the page is also unmassaged. LightGBM is retained for categorical/interaction handling and per-order SHAP, and the README states that explicitly rather than implying an accuracy win.
**Revisit if:** more data or richer graph features open a real gap — re-run and update the claim in both directions.

## 2026-09-01 — Publish the per-slice false-positive burden
**Decision:** `src/model/slices.py` reports, per customer slice, the share of **genuine** customers put through friction (`fp_rate_on_good`) and its rupee cost, plus the max/min disparity within each dimension. Surfaced in the docs, the notebook and an "Evidence" dashboard tab.
**Why:** Track 2 grades false-positive cost, and a portfolio-level rate hides who actually pays. A genuine tier-3 buyer is 3.8× more likely to be challenged than a tier-1 buyer. That is a real cost to real people; it is also the justification for the dynamic-friction design (verify, never block). Framed as an *operational harm audit*, not a legal fairness audit — no protected attribute is used and the variables involved are commercial.
**Revisit if:** the response ever becomes a hard block for any band — then the disparity stops being tolerable and needs mitigation, not just monitoring.

## 2026-09-01 — Published numbers are generated, and the README is tested
**Decision:** `python -m src.model.full_report` regenerates `docs/evaluation.md`, the figures and `reports/evaluation.json` from the code. `tests/test_published_claims.py` parses the README and asserts every headline figure against that JSON. CI rebuilds the dataset and model from scratch, regenerates the pack, and runs `--check` on it.
**Why:** A retyped statistic is a statistic that can drift, and on this project drift is indistinguishable from fabrication. The README is the most-read and least-tested file in any repository — so it gets a test. Tolerances are ~2% (cross-platform GBDT noise is not dishonesty) while the structural claims are exact.
**Revisit if:** the report grows expensive enough that CI regeneration becomes the slow step — then cache the artifact rather than loosening the check.

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
