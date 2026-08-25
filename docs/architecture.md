# Architecture

> Full narrative + the ASCII diagram live in [PLAN.md §5](../PLAN.md). This file will hold the exported architecture diagram (PNG) and any implementation notes as we build. Stub for now.

## The four layers (summary)
1. **Detector** — calibrated LightGBM → risk score + SHAP; IsolationForest anomaly signal alongside.
2. **Decision core** — deterministic rules **first** (Bumblebee pattern) → band by cost-optimal thresholds (GREEN / AMBER / RED).
3. **Response** — auto-responder for green/red; a bounded **LLM agent** investigates AMBER only (planner → typed tools → policy RAG → structured decision).
4. **HITL + immutable audit trail** — every decision logged; human can override.

Cross-cutting: **grounded explanation** (SHAP + retrieved policy → LLM reason code; narrates only provided facts).

## To add here as we build
- [ ] Exported diagram `docs/architecture.png`
- [ ] Sequence diagram of one order through the pipeline
- [ ] Data-flow + feature-store (offline==online) note
- [ ] Latency budget notes
