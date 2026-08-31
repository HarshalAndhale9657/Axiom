# Axiom — Claude Code Project Guide

AI Risk Manager for **COD/RTO fraud**, built for the **Razorpay AI Buildathon (Track 2)**.
This file tells Claude Code how to work in this repo. **The plan of record is [PLAN.md](PLAN.md) — read it before any build task.** Deeper docs live in `docs/`.

## Non-negotiable constraints (read every session)
- **Deadline:** ~5 Sep 2026 (verify on form). **Solo** builder, **all-in**. Do **not** overscope — one rehearsed golden-path demo beats five half-features.
- **Budget: $0.** No Anthropic key. The LLM layer runs on **free tiers** (Gemini primary; Groq/local Ollama fallback) behind a **provider-agnostic interface**. Reserve the OpenAI ~$2.44 for the final demo only.
- **Defense-only.** Scoring / flagging / verifying / protective actions only. **Nothing offense-capable** (no evasion, no fraud-generation). If a task drifts offensive, stop and flag it.
- **Honesty is the grade.** Track 2 rewards honest metrics + false-positive cost. Never cherry-pick, hide failures, or claim results that weren't actually run.

## The sacred ML rules (leakage discipline — our differentiator)
- **Split by TIME**, never a random shuffle. The **test set keeps the natural RTO rate** (never resampled).
- **Out-of-fold / training-only** encoding for pincode-risk & buyer-history features. A label must never leak into its own feature.
- Any resampling (SMOTE/class-weights) happens **inside** the CV pipeline on the **training fold only** (`imblearn.Pipeline`).
- **Calibrate** probabilities (isotonic) — the whole cost story depends on it.
- Headline metric is **PR-AUC + the BMR rupee cost curve**, *never* accuracy.
- **The operating threshold is a hyper-parameter: fit it on validation, freeze it, score test once.** Never quote the minimum of a cost curve swept on the test split — that is an oracle. `src/model/threshold.py` owns this; the optimism gap is published, not hidden.
- **Respect the outcome-availability lag** (`outcome_lag_days`, default 7). A label-derived feature may only count orders whose outcome had already resolved — an order placed today cannot know whether yesterday's was returned.
- **Every headline number needs an interval** (`bootstrap_ci`) and a **non-trivial baseline** (`src/model/baselines.py`). Where an interval spans zero, report the null result.
- If unsure whether something leaks, assume it does and verify.

## Published numbers are generated, not typed
`python -m src.model.full_report` regenerates `docs/evaluation.md`, the figures and `reports/evaluation.json`; `--check` audits the pack. `tests/test_published_claims.py` tests the README against that JSON. **After any retrain, re-run the report and fix whatever the claim tests flag** — never edit a number by hand.

## Tech stack
Python 3.10+ · **LightGBM** (primary) + **IsolationForest** (anomaly layer) · **SHAP** · **FastAPI** · provider-agnostic **LLM (Gemini free, OpenAI fail-over)** · **TF-IDF** policy RAG (ChromaDB was dropped — the corpus is small and the dependency was not earned) · **NetworkX** ring detection · **SQLite** (append-only audit) · **Next.js 16** dashboard.

## Repo map
- `PLAN.md` — master plan (strategy, architecture, day-by-day). **Source of truth.**
- `docs/project/` — `GOALS.md` (what we want), `DECISIONS.md` (why we chose things), `PROGRESS.md` (live tracker), `GLOSSARY.md`.
- `docs/conventions/` — `python.md`, `ml-practices.md`, `testing.md`.
- `docs/policy/rto_cod_risk_policy.md` — risk rules **and** the agent's RAG knowledge base.
- `docs/architecture.md`, `docs/evaluation.md` — design + the honest-metrics writeup.
- `src/` — `data` · `features` · `model` (train · evaluation · **threshold** · **baselines** · **slices** · **full_report** · explain · anomaly) · `rules` · `agent` · `rag` · `graph` · `actions` · `audit` · `api`.
- `MODEL_CARD.md` — intended use, limitations, ethical considerations. `docs/pitch.md` — the 5-min pitch beat sheet.
- `notebooks/` — EDA + the crown-jewel `03_evaluation.ipynb`.

## Commands
- Setup: `pip install -r requirements.txt`
- Generate data: `python -m src.data.generate_synthetic_cod --n 20000 --seed 42`
- Tests: `pytest -q`
- Train + freeze thresholds: `python -m src.model.train`
- Regenerate every published number: `python -m src.model.full_report`
- Rebuild and re-audit everything: `make verify`
- Serve API: `uvicorn src.api.main:app --reload` · Dashboard: `npm --prefix web run dev`

## Code style
- Type hints on function signatures; f-strings; Python 3.10+.
- **Black** (line length 100) + **isort** before committing (config in `pyproject.toml`).
- Pure functions for features; **deterministic seeds everywhere** (reproducibility is graded).
- Small, reviewable commits using **Conventional Commits** with a scope: `feat(data): …`, `fix(model): …`, `test(data): …`, `docs: …`, `chore: …`.

## Working agreement (how to help me)
- Before a build task: skim `PLAN.md` + the relevant `docs/conventions/*`.
- After a meaningful change: tick `docs/project/PROGRESS.md`; if a real choice was made, log it in `docs/project/DECISIONS.md`.
- Keep the **evaluation notebook central** — it is the grade.
- **Flag scope creep.** Prefer finishing the golden path over adding breadth.
- **Verify before claiming** — run the test/command and show output before saying something works.

## Status
Feature-complete and evaluation-hardened (**175 tests green**). Detector, bounded agent, cross-vendor verifier, batch mode, copilot, ring graph, real Razorpay test-mode actions, immutable audit, Next.js console, CI, Docker, model card, generated evidence pack.
**Remaining before the ~5 Sep deadline: record the 5-min pitch (`docs/pitch.md`), add README screenshots, submit early.** Scope is frozen — do not add features. See `docs/project/PROGRESS.md`.
