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
- ⏭️ **NEXT (P2b):** baseline calibrated LightGBM → first honest PR-AUC

## Phase checklist (compressed ~10-day plan)
- [x] **P1 — Data:** causal synthetic COD generator + tests ✓ (real-pincode grounding + EDA notebook = next)
- [ ] **P2 — Features:** leakage-safe pipeline (time split, OOF encoders) + baseline LightGBM
- [ ] **P3 — Model:** tuning + calibration + SHAP + IsolationForest anomaly layer
- [ ] **P4 — ★ Evaluation:** BMR rupee cost curve, PR-AUC, precision@k, calibration, failure-mode matrix, leakage/baseline comparisons
- [ ] **P5 — Decision core + API:** deterministic rules/banding + tiered actions + FastAPI + SQLite audit store
- [ ] **P6 — Agent:** provider-agnostic LLM tools + planner + structured decision + grounded reason codes + policy RAG + HITL
- [ ] **P7 — Dashboard:** order queue + case detail (score/SHAP/reason/agent trace/citations/action) + live threshold slider + audit view + override
- [ ] **P8 — Ship:** golden-path integration + Dockerize + industry-grade README + architecture diagram + record demo + **5-min pitch video** + submit early

## Blockers / to-verify
- [ ] Confirm deadline + whether the build is submitted *with* the application or after shortlisting (Google Form).
- [ ] Confirm solo is allowed.
- [ ] Check if the buildathon grants Anthropic/AWS API credits.
- [ ] Get a Google account / Gemini free API key.

## Session log
- **2026-08-26** — Analyzed buildathon; chose Track 2 / RTO / "Axiom"; ran 4 parallel research streams; wrote `PLAN.md` and upgraded to v2 by merging the user's research PDF (BMR, anomaly layer, address-quality score, dynamic friction, failure-mode matrix; scoped GNN/DP as stretch). Set free-LLM budget plan. Researched CLAUDE.md best practices and built repo scaffolding + project-management docs. Initialized git + pushed to GitHub.
- **2026-08-26 (P1)** — Built the causal synthetic COD generator: per-payment intercept calibration (COD 27% / prepaid 4%), fraud-ring (shared-device, bursty, mule-identity) + buyer-recurrence structure, malformed-vs-clean addresses, and hidden ground-truth latents written to a separate file for leakage-safety. 10 pytest tests pass (schema, leakage guard, realistic rates, tier gradient, reproducibility). Committed + pushed.
