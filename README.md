<!-- Line 1 = the problem. Line 2 = demo link. Line 3 = a GIF. (Judges & recruiters read this first.) -->
# 🛡️ Axiom — AI Risk Manager for COD / RTO Fraud

**Blocking a good customer costs ~13× more than the fraud you stop — yet risk teams get a black-box score with no *why*.** Axiom scores every order for return-to-origin (RTO) / fraud risk, **explains the score**, **investigates borderline cases against policy with a Claude agent**, and drives a **bounded, auditable, defense-only** response — with a human in the loop.

> 🎥 **Demo video:** _<link — add after recording>_
> 🖼️ _<demo.gif — add after build>_

Built for the **Razorpay AI Buildathon · Track 2 (AI Risk Manager)**. Built with **Claude (Opus 4.8 / Sonnet 4.6)** on the Claude Agent SDK.

---

## Why this matters (the numbers)
- COD RTO in India runs **20–40%** vs **2–8%** prepaid; ~**60%** of orders are COD.
- Each RTO costs a merchant **₹450–900** + tied-up inventory; D2C brands lose ~**₹8,000 Cr/yr**.
- False declines cost merchants **~13×** more than actual fraud; **33%** of shoppers never return after one.

**So the goal is not "catch all fraud" — it's to minimize total business cost, honestly measured.** That is exactly what Axiom optimizes and reports.

---

## What it does (detector · verifier · auto-responder — all three)
1. **Detector** — calibrated LightGBM → per-order RTO risk score + SHAP attributions.
2. **Verifier** — address/pincode-serviceability check + optional OTP/confirmation that can *downgrade* risk.
3. **Auto-responder** — bounded tiered actions: `green → frictionless` · `amber → step-up / COD→prepaid nudge` · `red → hold / escalate`.
4. **Explain + investigate (Claude)** — SHAP + retrieved policy → a *grounded* reason code; a bounded agent investigates borderline cases and cites policy.
5. **HITL + immutable audit trail** — every decision is logged and human-overridable.

---

## Architecture
_See [docs/architecture.md](docs/architecture.md)._ Deterministic rules run **before** the LLM (Razorpay-Bumblebee pattern); the agent only investigates the **borderline** band; the LLM **never overrides** the score — it explains and recommends within policy.

---

## Honest metrics (the point of Track 2)
_See [docs/evaluation.md](docs/evaluation.md) and [notebooks/03_evaluation.ipynb](notebooks/03_evaluation.ipynb)._
- PR-AUC vs the prevalence baseline (not accuracy — accuracy is banned here and we explain why).
- precision@k, calibration curve.
- **Rupee-denominated cost-vs-threshold curve** selecting the cost-optimal operating point τ\*.
- **Leakage-avoidance statement** + comparison vs a deliberately-leaky model and a naïve "block-all-COD" baseline.

---

## Defense-only
Axiom is **strictly defensive**: it scores, flags, verifies, and applies protective actions to shield the platform and honest customers. It contains **nothing offense-capable**.

---

## Quickstart
```bash
cp .env.example .env      # add your ANTHROPIC_API_KEY
docker compose up         # or: pip install -r requirements.txt
python -m src.data.generate_synthetic_cod --n 20000 --seed 42
# train, serve, and open the dashboard — see docs/
```

## Tech
Python · LightGBM · SHAP · FastAPI · Claude Agent SDK · ChromaDB (RAG) · SQLite (audit) · Next.js dashboard.

## Status
🚧 In active development for the buildathon. See [PLAN.md](PLAN.md) for the full build plan and day-by-day.
