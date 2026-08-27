<!-- Line 1 = the problem. Line 2 = the demo. Line 3 = proof. (Judges & recruiters read this first.) -->
# 🛡️ Axiom — AI Risk Manager for COD / RTO Fraud

> **Blocking a good customer costs ~13× more than the fraud you stop — yet risk teams get a black-box score with no *why*.**
> Axiom scores every order for return-to-origin (RTO) risk, **explains it**, **investigates borderline cases against policy with a bounded agent**, and drives an **auditable, defense-only** action — optimised for **rupee cost**, not a leaderboard number.

<p>
<img alt="Razorpay AI Buildathon · Track 2" src="https://img.shields.io/badge/Razorpay%20AI%20Buildathon-Track%202%20·%20AI%20Risk%20Manager-2563eb">
<img alt="tests" src="https://img.shields.io/badge/tests-70%20passing-16a34a">
<img alt="python" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
<img alt="next.js" src="https://img.shields.io/badge/dashboard-Next.js%2016-111827">
<img alt="posture" src="https://img.shields.io/badge/posture-defense--only-475569">
<img alt="budget" src="https://img.shields.io/badge/budget-%240%20free%20tier-16a34a">
<img alt="license" src="https://img.shields.io/badge/license-MIT-64748b">
</p>

**Built for the Razorpay AI Buildathon (Track 2).** A calibrated **LightGBM** detector + **SHAP** explanations + a **bounded Gemini agent** (policy RAG, structured decisions) + an **immutable audit trail** — served through a **FastAPI** backend and a **Next.js** risk console. Runs on a **$0 free tier**.

> 🎥 **Demo video:** _<add link — record the one-click "Play demo" walkthrough>_

---

## Architecture

![Axiom architecture — decision pipeline](docs/architecture.svg)

**Four layers, one bounded path** (mirrors Razorpay's own Bumblebee / RTO-Shield design):

1. **Detector** — a calibrated LightGBM outputs a per-order RTO probability + **SHAP** attributions; an **IsolationForest** adds an unsupervised trip-wire for zero-day / cold-start.
2. **Decision core** — **deterministic rules run *before* the LLM** (highest precision), then the score is banded by **cost-optimal thresholds** into GREEN / AMBER / RED.
3. **Response** — GREEN/RED get an instant bounded action; **only AMBER** reaches the agent: a planner runs typed tools, retrieves policy via RAG, and emits a **schema-constrained** decision the LLM can never step outside of.
4. **HITL + immutable audit** — every decision and human override is logged to an append-only store (DB-enforced).

*Cross-cutting:* reason codes are **grounded** — the LLM narrates only the SHAP factors + retrieved policy it's given, and **never overrides the score**.

---

## Honest metrics — the point of Track 2

The bar is *"honest metrics including false-positive cost."* So our headline isn't an AUC — it's a **rupee cost curve**. We sweep the decision threshold, pick the cost-minimising **τ\*** (Bayes Minimum Risk), and show it sits far below the naive 0.5.

![BMR rupee cost curve](docs/figures/cost_curve.png)

**The money story (held-out test split, ₹ per 1,000 orders):**

| Policy | Cost / 1k orders |
|---|---:|
| Approve everything | ₹64,795 |
| **Naive "block all COD"** | **₹71,776** ← *worse than doing nothing* |
| **Axiom @ τ\*** | **₹49,254** |

→ **31% cheaper than block-all-COD**, **24% cheaper than approving everything.** That "block-all-COD is worse than nothing" result *is* the false-positive-cost argument, made in rupees.

| | |
|---|---|
| ![Precision-Recall](docs/figures/pr_curve.png) | ![Calibration](docs/figures/calibration.png) |

- **PR-AUC 0.51** vs a 0.17 prevalence baseline (**3.0×**) — ROC-AUC **0.80**, deliberately *not* a fake 0.99.
- **Well-calibrated** (Brier 0.108) — required for the cost math to mean anything.
- **Leakage-safe by construction:** time-based split, **out-of-fold** encoding for pincode/buyer history (proven: first-sighting encoding == prior, deviation `0.0`), test set never resampled. A guard test fails if any feature can see its own label.

> Accuracy is **intentionally never reported** — at ~19% RTO it rewards a model that catches nothing.

---

## What it does (all three Track-2 modalities)

- **Detector** — calibrated RTO risk score + SHAP driver bars.
- **Verifier** — address-quality / pincode-serviceability checks that can *downgrade* risk on verification.
- **Auto-responder** — a bounded, tiered **dynamic-friction** engine: `green → frictionless` · `amber → step-up / part-pay / COD→prepaid` · `red → hold / escalate`. A mis-flagged good customer is *verified*, never silently banned.

**Meaningful AI, bounded:** the Gemini agent plans typed tools (`get_buyer_history`, `check_address`, `get_pincode_risk`, `check_velocity`), retrieves the relevant `RTO-POL-*` policy clauses, and returns a validated JSON decision from a **closed action set** — with a deterministic fallback if the LLM is unavailable.

---

## Quickstart

**Prerequisites:** Python 3.10+, Node 18+. A free **Gemini** key is optional (the agent/reason-codes fall back to deterministic output without one — everything still runs).

```bash
# 1) Backend
pip install -r requirements.txt
python -m src.data.generate_synthetic_cod --n 20000 --seed 42   # reproducible seed data
python -m src.model.train                                        # train + calibrate (~10s)
cp .env.example .env                                             # (optional) add GEMINI_API_KEY
uvicorn src.api.main:app --reload                                # API → http://127.0.0.1:8000

# 2) Dashboard (new terminal)
npm --prefix web install
npm --prefix web run dev                                         # console → http://localhost:3000
```

With `make` installed you can shortcut: `make setup` · `make data` · `make api` · `make web` · `make test` · `make figures`.

A free Gemini key: [aistudio.google.com](https://aistudio.google.com) → *Get API key* (Google account, no card). Then `GEMINI_API_KEY=...` in `.env`.

---

## The dashboard

A production-grade risk console (light + **dark** mode) — **click "Play demo"** for a hands-free walkthrough (select → investigate → override → tour).

<!-- Add screenshots to docs/screenshots/ then uncomment:
| Risk queue + case detail | Economics (BMR + ₹ confusion matrix) |
|---|---|
| ![queue](docs/screenshots/dashboard-light.png) | ![economics](docs/screenshots/economics.png) |
| ![dark](docs/screenshots/dashboard-dark.png) | ![agent](docs/screenshots/case-detail.png) |
-->

- **Risk Queue** — filterable, banded, rupee-at-risk per order.
- **Case detail** — SHAP driver bars → live agent trace (tool evidence + policy citations + confidence) → human override.
- **Economics** — the interactive BMR cost curve, a **₹ confusion matrix** at any threshold, and a live decision-flow pipeline.
- **Audit Trail** — the immutable log with before→after overrides.

---

## Why this wins (Track-2 rubric map)

| Requirement | How Axiom satisfies it |
|---|---|
| Detector · verifier · auto-responder | All three present and demonstrable |
| Measured precision / recall | PR-AUC vs prevalence, precision@k, per-band confusion on an untouched time-split test set |
| **Honest metrics incl. false-positive cost** | Rupee BMR cost curve + τ\*, ₹ confusion matrix, leakage-avoidance statement, naive-baseline + deliberately-leaky comparisons |
| **Strictly defense-only** | Scores / flags / verifies / protects only — nothing offense-capable |
| Meaningful AI | Bounded agent (tools + policy RAG + structured decisions) + grounded SHAP→LLM reason codes |
| Auditable & bounded | Rules-before-LLM, closed action set, immutable HITL audit |

---

## Tech stack
Python · **LightGBM** + **IsolationForest** · **SHAP** · **FastAPI** · **SQLite** (immutable audit) · provider-agnostic LLM on **Gemini** (free) · **ChromaDB/TF-IDF** policy RAG · **Next.js 16** + Tailwind + Recharts.

## Testing
`pytest -q` → **70 tests**, including leakage guards, a hand-checked cost example, τ\* < 0.5, closed-action-space checks, and API/audit round-trips.

## Repo map
`src/` — `data` · `features` · `model` · `rules` · `agent` · `rag` · `audit` · `api` · `web/` — the dashboard · `docs/` — plan, policy, evaluation, figures · `notebooks/` — EDA + evaluation.
See **[PLAN.md](PLAN.md)** for the full strategy and **[docs/](docs/)** for conventions, policy, and decisions.

## Defense-only & honesty
Axiom is **strictly defensive** — it contains nothing offense-capable. Every metric here was actually run; a stated limitation: the demo uses a **synthetic, causal COD dataset** (grounded in real Indian RTO drivers) because no clean public COD-RTO dataset exists — disclosed openly, and the pipeline is designed to run identically on real orders.

## License
[MIT](LICENSE) · © 2026 Harshal Andhale
