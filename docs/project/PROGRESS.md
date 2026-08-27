# Progress Tracker

**Today:** 2026-08-26 · **Deadline:** ~2026-09-05 (⚠️ verify on form) · **Days left:** ~10 · **Builder:** solo, all-in

> ⚠️ **Timeline note:** PLAN.md §12 was written with an Aug 23 start (13 days). Real start is **Aug 26 (~10 days)**. Treat the §12 dates as indicative; this tracker is the live source of truth. We keep the same phase order, slightly compressed, with Days 8–10 reserved for polish + pitch so slippage never threatens submission.

## Now / Next
- ✅ Deep research (4 streams) + track/product decision
- ✅ `PLAN.md` v1 → **v2** (merged the user's research PDF)
- ✅ Budget plan (free-LLM, provider-agnostic)
- ✅ Repo scaffolding + project-management docs
- ✅ Git repo live on GitHub (github.com/HarshalAndhale9657/Axiom)
- ✅ **P1 — synthetic COD data generator** (`src/data/generate_synthetic_cod.py`) + **10 passing tests**. Realistic: COD 27% / prepaid 4% RTO, tier gradient, fraud-ring & repeat-buyer signals; hidden latents split out for leakage-safety.
- ✅ **P2a — leakage-safe feature pipeline** (`src/features/build_features.py`): 22 features (as-of target encoding, velocity, graph/ring), chronological split, train-only prior. **8 tests incl. leakage guards** — first-sighting enc == prior, deviation `0.0`.
- ✅ **P2b — baseline calibrated LightGBM** (`src/model/train.py`): honest **TEST PR-AUC 0.512 vs 0.169 baseline (3.0×), ROC-AUC 0.799, Brier 0.108**. Natural distribution + isotonic calibration on val; test untouched. 4 tests pass.
- ✅ **P4 ★ — honest cost-based evaluation** (`src/model/evaluation.py`): **BMR rupee cost curve, τ\*=0.21** (not 0.5), example-dependent costs, precision@k, calibration table, 3 figures. **Axiom @ τ\* costs ₹49.3k/1k orders — 31% less than block-all-COD (₹71.8k), 24% less than approve-all (₹64.8k).** Killer insight: naive block-all-COD is *worse* than doing nothing. 7 tests (incl. hand-checked cost, τ\*<0.5, beats naive).
- ✅ **P3b — SHAP explanations + IsolationForest anomaly** (`src/model/explain.py`, `src/model/anomaly.py`): per-order grounded factors + plain-English labels (the facts the LLM may narrate); unsupervised defense-in-depth trip-wire. 7 tests.
- ✅ **P5a — deterministic decision core** (`src/rules/decision_core.py`): rules-before-banding, **closed bounded action space**, tiered dynamic friction, anomaly trip-wire, every action cites a policy clause. 11 tests.
- ✅ **P6a — provider-agnostic LLM layer + grounded reason codes** (`src/agent/llm.py`, `src/agent/reason_code.py`): Gemini free-tier via lightweight REST (**key validated live**; thinking-budget fix for clean output), `MockProvider` for offline tests, grounded prompt that narrates only SHAP factors + policy (never invents) with a deterministic fallback. 4 tests + live-verified.
- ✅ **P6b — bounded investigation agent + policy RAG** (`src/agent/investigate.py`, `src/agent/tools.py`, `src/rag/policy.py`): planner → typed tools → TF-IDF policy retrieval → **schema-constrained** LLM decision, validated to the closed action set with deterministic fallback. **Live-verified on Gemini** (real structured, policy-cited recommendation). 10 tests.
- ✅ **P5b — FastAPI service + immutable audit trail + HITL** (`src/api/`, `src/audit/store.py`): RiskEngine orchestrates score → decide → investigate; SQLite audit is append-only (DB triggers block UPDATE/DELETE); human override logged with before/after. **Live HTTP smoke passed** (queue → detail → agent → override → audit → metrics). 9 tests.
- ✅ **P7 — Next.js 16 dashboard** (`web/`): premium enterprise console — KPI header, filterable risk queue, case detail (SHAP bars + live agent trace + HITL override), interactive **BMR threshold slider** (Recharts), immutable audit table. Type-checks + builds clean; calls the live API. Added `/costcurve` endpoint.
- ✅ **P7+ — UI/UX elevations:** dark-mode toggle (design-token system), count-up KPIs + skeleton loaders + smooth transitions, **₹ confusion-matrix panel + live decision-flow diagram** (Economics tab), and one-click **Demo mode** (auto-walkthrough: select → investigate → override → tour). Frontend typechecks clean; backend cost curve now emits confusion cells + ₹ split.
- ✅ **P8a — industry-grade README** (`README.md`): badges, embedded **architecture SVG** + **BMR cost-curve / PR / calibration** figures, the rupee money-story table, Track-2 rubric map, one-command Quickstart + `Makefile`. Diagram at `docs/architecture.svg`; figures in `docs/figures/`.
- ✅ **B-series — "not dummy data" moves:** **B1** real Razorpay **test-mode** payment links (`src/actions/razorpay_actuator.py`, live-verified) for convert-to-prepaid / part-pay; **B2** interactive **fraud-ring graph** (`src/graph/rings.py`, validated vs the hidden `is_ring` latent) with a force-directed web view; **B3** live **leaky-vs-honest toggle** (`/leakage`) weaponizing the 0.51 PR-AUC.
- ✅ **C2 — cross-vendor adversarial verifier** (`src/agent/verify.py`): an independent **OpenAI `gpt-4o-mini`** second-checks the Gemini agent's amber action (agree/veto); a veto escalates to a human. **Live-verified** (grounded→agree, over-aggressive→veto). UI shows the named verifier and — honestly — whether it was truly cross-vendor.
- ✅ **C1 — autonomous batch mode** (`src/agent/batch.py`, `POST /batch/run`, "Batch" dashboard tab): works the whole amber queue under **real stopping rules** (max-N · call-budget · consecutive-low-value · quiet-hours); reports honest 2×2 **₹ economics** — gross recovered − friction cost on genuine customers = **net**, measured on the labelled held-out test batch. Every decision audited. **Live-verified** (net ₹809/8 orders).
- ✅ **Provider fail-over + honesty flag** (`FallbackProvider`, `AXIOM_LLM_PROVIDER=auto`): Gemini free-tier → **automatic OpenAI fail-over on 429/quota**, so the agent keeps reasoning at ~$0.001/batch. The verifier's "independent" claim now **tracks the vendor that actually served** — never overclaims cross-vendor when a fail-over made both the same. 97 tests green.
- ✅ **C3 — grounded analyst copilot** (`src/agent/copilot.py`, `POST /orders/{id}/ask`, chat box in the case detail): read-only Q&A that answers **only** from the case record (order facts + SHAP drivers + current recommendation + retrieved policy), cites the policy ids it used, and says *"That isn't in the case record"* when asked something off-file. Invented citations are filtered out. **Live-verified**: "why flagged?" → grounded + cited; "what if the buyer verifies?" → conditional policy reasoning; "favorite color?" → correctly refused.
- ⏭️ **NEXT:** D-series — SHAP waterfall visual, counterfactual what-if recourse, per-merchant economics on the cost slider, model card + provenance.

## Phase checklist (compressed ~10-day plan)
- [x] **P1 — Data:** causal synthetic COD generator + tests ✓ (real-pincode grounding + EDA notebook = next)
- [ ] **P2 — Features:** leakage-safe pipeline (time split, OOF encoders) + baseline LightGBM
- [x] **P3 — Model:** calibration + SHAP explanations + IsolationForest anomaly ✓
- [x] **P4 — ★ Evaluation:** BMR rupee cost curve (τ\*), PR-AUC, precision@k, calibration, baseline comparisons ✓ (failure-mode matrix → in the eval notebook next)
- [x] **P5 — Decision core + API + audit:** rules/banding/tiered actions + FastAPI service + immutable SQLite audit + HITL override ✓ (live HTTP smoke)
- [x] **P6 — Agent:** LLM provider + grounded reason codes + bounded agent (typed tools + policy RAG + schema-constrained structured decision) ✓ (live Gemini); HITL override wired at the API next
- [x] **P7 — Dashboard:** queue + case detail (score/SHAP/reason/agent trace/citations/action) + live threshold slider + audit view + HITL override ✓ (Next.js 16, builds clean)
- [ ] **P8 — Ship:** golden-path integration + Dockerize + industry-grade README + architecture diagram + record demo + **5-min pitch video** + submit early

## Blockers / to-verify
- [ ] Confirm deadline + whether the build is submitted *with* the application or after shortlisting (Google Form).
- [ ] Confirm solo is allowed.
- [ ] Check if the buildathon grants Anthropic/AWS API credits.
- [ ] Get a Google account / Gemini free API key.

## Session log
- **2026-08-26** — Analyzed buildathon; chose Track 2 / RTO / "Axiom"; ran 4 parallel research streams; wrote `PLAN.md` and upgraded to v2 by merging the user's research PDF (BMR, anomaly layer, address-quality score, dynamic friction, failure-mode matrix; scoped GNN/DP as stretch). Set free-LLM budget plan. Researched CLAUDE.md best practices and built repo scaffolding + project-management docs. Initialized git + pushed to GitHub.
- **2026-08-26 (P1)** — Built the causal synthetic COD generator: per-payment intercept calibration (COD 27% / prepaid 4%), fraud-ring (shared-device, bursty, mule-identity) + buyer-recurrence structure, malformed-vs-clean addresses, and hidden ground-truth latents written to a separate file for leakage-safety. 10 pytest tests pass (schema, leakage guard, realistic rates, tier gradient, reproducibility). Committed + pushed.
- **2026-08-28 (C-series agentic upgrades)** — Shipped **C2** (cross-vendor adversarial verifier, OpenAI checks Gemini), **C1** (autonomous batch mode with real stopping rules + honest net-₹ economics on the labelled test batch, new "Batch" dashboard tab), and **C3** (grounded analyst copilot — read-only Q&A that answers only from the case record + policy, cites what it used, and refuses off-file questions). Hit Gemini free-tier **429 quota exhaustion** during batch runs → added a provider-agnostic **`FallbackProvider`** (Gemini→OpenAI `auto`) so the agent keeps reasoning at ~$0.001/batch; made the verifier's independence claim **track the vendor that actually served** (no overclaiming). All live-verified against real APIs. **101 tests green**, web typecheck clean.
