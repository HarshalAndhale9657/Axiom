# Axiom — Master Plan
### AI Risk Manager for COD / RTO Fraud · Razorpay AI Buildathon (Track 2)

> **Product name:** **Axiom** — *an axiom is a self-evident truth accepted as a foundation.* Fitting for a risk system whose whole edge is **honest, provable metrics**. Long-form: **A**gentic, e**X**plainable **I**ntelligence for **O**rder-risk **M**anagement. Tagline: *"Risk decisions you can prove."*
> **One line:** *A strong ML model decides the risk; Claude explains the "why," investigates the case against policy, and recommends a bounded, auditable defensive action — with a human in the loop on anything uncertain.*
> **Owner:** Solo · **Mode:** All-in (6+ hrs/day) · **Deadline:** ~Sep 5, 2026 (VERIFY on form) · **Compiled:** 2026-08-23

---

> ⚠️ **Status: this is the plan as written on 2026-08-23, kept for provenance — not a description of what shipped.**
> Two things diverged deliberately during the build and are logged in
> [docs/project/DECISIONS.md](docs/project/DECISIONS.md):
> **(1)** the agent runs on **Gemini (free tier) with an OpenAI fail-over over plain REST**, not the
> Claude Agent SDK — there was no Anthropic budget, and the provider-agnostic interface was the
> honest way to keep the design intact; **(2)** the evaluation is considerably stricter than §9
> planned (threshold fitted out-of-sample, outcome-availability lag, baseline ablation with paired
> intervals, per-slice false-positive audit).
> For what the system actually does today, read [README.md](README.md),
> [docs/architecture.md](docs/architecture.md) and [docs/evaluation.md](docs/evaluation.md).

## 0. How to use this document
This is the single source of truth for the build. Sections 1–4 are the *strategy* (why we win). Sections 5–11 are the *spec* (what to build). Section 12 is the *day-by-day*. Sections 13–16 are *pitch, risk, and the winning checklist*. **Re-read Section 4 before every major decision** — winning teams map every choice back to the rubric.

---

## 1. The Winning Thesis (why this wins)

Four research streams converged on one conclusion:

1. **Razorpay rebuilt its entire risk stack on the Claude Agent SDK** — the exact tooling we build on. Their named products: **Thirdwatch / RTO Shield** (COD order scoring), **Bumblebee** (multi-agent merchant-risk review: *Planner → parallel Fetchers → Analyzer that runs deterministic rules before the LLM*), **Dispute Responder**, **ADA** (real-time anomaly detection), **Razorpay Capital dedup** (Good/Bad/Grey tiering). **If our architecture mirrors theirs, the panel recognizes their own design and sees we understand *why* it wins.**

2. **RTO on COD is their most-talked-about India problem.** COD RTO runs **20–40%** vs **2–8%** prepaid; ~**60%** of Indian orders are COD; each RTO costs **₹450–900** + tied-up inventory; D2C brands lose ~**₹8,000 Cr/yr**. It maps 1:1 to Thirdwatch. It also has the *cleanest* false-positive-cost story: a wrongly-blocked good order = a lost sale + a damaged customer.

3. **The evaluation IS the grade, not the model.** The bar literally says *"honest metrics including false-positive cost."* A **calibrated LightGBM** evaluated rigorously beats a fancy GNN evaluated sloppily. Public RTO models online brag ~0.99 AUC that is almost certainly **leaking the label** — we win by *out-honesting* them: leakage-safe features + a **rupee-denominated cost-vs-threshold curve**.

4. **Meaningful AI = wrap the classifier, don't replace it.** The LLM's job is explanation, investigation, and bounded recommendation — never overriding the score. This is exactly the "bounded, auditable, defense-only" story the track rewards.

**Our unfair advantage as a solo ML builder:** we go *deep* on the one thing that is the actual grade (honest cost-based evaluation), and we *mirror Razorpay's own agent architecture* on top. Depth + alignment, not breadth.

---

## 2. Product Definition

**Axiom scores every incoming order for RTO/fraud risk and drives a tiered, defensive, fully-auditable response** — covering all three modalities the track names (**detector + verifier + auto-responder**), which most entrants won't:

- **Detector** — a calibrated gradient-boosted model outputs a per-order RTO risk score + SHAP attributions.
- **Verifier** — an address normalizer / pincode-serviceability check / optional OTP-confirmation step that can *downgrade* risk when the buyer verifies (friction only when risk is elevated).
- **Auto-responder** — a **bounded, tiered "Dynamic Friction" engine** (friction scales with risk, so a mis-flagged good customer is *verified*, never silently banned): `green → frictionless` · `amber → step-up (OTP / address-confirm / COD→prepaid nudge / part-pay deposit "skin in the game")` · `red → hold / convert / escalate to human`. Every action is explainable, rule-gated, and logged. Dynamic Friction is the mechanism that *actively manages false-positive cost* — our headline metric.

On top of the ML core sit the four "meaningful AI" layers (Section 5).

---

## 3. Alignment with Razorpay (speak their language)

| Razorpay's real system | Our echo in Axiom |
|---|---|
| **Thirdwatch / RTO Shield** — pre-dispatch COD scoring, red/green flag | Our core RTO risk scorer + banding |
| **Bumblebee** — Planner → parallel Fetchers → Analyzer (rules before LLM) | Our multi-agent investigation layer, same shape |
| **Razorpay Capital** — Good / Bad / Grey, grey → human | Our green / red / amber, amber → human review |
| **PrePay COD** — convert risky COD to prepaid via payment link | Our "COD→prepaid nudge" auto-response action |
| **Dispute Responder / audit needs** | Our immutable audit trail + reason codes |
| **Vulcan** (criticized as opaque, unvalidated) | Our headline is **explainability + honest metrics** — the exact gap |

**Pitch anchors (memorize):** COD RTO 20–40% vs 2–8% prepaid · ₹450–900 lost/RTO · ~60% orders COD · false declines cost merchants ~13× actual fraud · 33% of shoppers won't return after one false decline.

---

## 4. How We Satisfy EVERY Track-2 Bar (the rubric map)

> Track 2: *"Develop detectors, verifiers, or auto-responders for fraud, returns, or chargebacks with measured precision/recall metrics."* Bar: *"Honest metrics including false-positive cost. Strictly defense-only: anything offense-capable is disqualified."*

| Requirement | How Axiom nails it |
|---|---|
| **Detector** | Calibrated LightGBM RTO risk scorer with SHAP |
| **Verifier** | Address/serviceability normalizer + OTP/confirmation that downgrades risk |
| **Auto-responder** | Bounded tiered action engine (approve / step-up / COD→prepaid / hold / escalate) |
| **Measured precision/recall** | PR-AUC (vs prevalence baseline), precision@k, recall@precision, per-band confusion matrices on an untouched **time-based** test set |
| **Honest metrics incl. false-positive cost** | Rupee-denominated confusion matrix + **cost-vs-threshold curve** selecting τ\*; explicit **leakage-avoidance** statement; comparison vs a naïve "block-all-COD" baseline *and* a deliberately-leaky model to show the difference |
| **Strictly defense-only** | Scoring / flagging / verification / protective actions only. No evasion tooling, no offense. Stated explicitly in README + pitch. Every action protects the platform *and* good customers |
| **Submission = repo + 5-min video + architecture** | Industry-grade README, one-command run, architecture diagram, golden-path demo, honest-metrics section |

---

## 5. Architecture

```
                          ┌────────────────────────────────────────────────────┐
   Incoming order  ───▶   │  0. INGEST & FEATURE BUILD (offline == online)      │
   (JSON)                 │     address quality · pincode risk (OOF) · buyer    │
                          │     history (OOF) · velocity/graph · COD · distance │
                          └───────────────────────┬────────────────────────────┘
                                                  ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  1. DETECTOR   Calibrated LightGBM → risk_score ∈ [0,1]  + SHAP values     │
   └───────────────────────┬──────────────────────────────────────────────────┘
                           ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  2. DECISION CORE (deterministic FIRST, like Bumblebee/Capital)           │
   │     hard rules (blacklist, non-serviceable, verified-repeat-buyer) →       │
   │     band by cost-optimal thresholds → GREEN / AMBER(grey) / RED            │
   └───────────────┬───────────────────────────────┬──────────────────────────┘
        GREEN/RED  │ (auto, logged)         AMBER   │ (borderline only)
                   ▼                                ▼
   ┌───────────────────────────┐   ┌───────────────────────────────────────────┐
   │ 3a. AUTO-RESPONDER        │   │ 3b. CLAUDE AGENT (bounded investigation)   │
   │  green→frictionless       │   │  Planner → tools: get_buyer_history,       │
   │  red→hold/convert/escalate│   │  check_address, pincode_risk, velocity,    │
   └───────────────────────────┘   │  search_policy(RAG) → structured JSON:     │
                   │               │  {action, confidence, evidence[],          │
                   │               │   policy_citations[], reason_code}         │
                   │               └───────────────────┬───────────────────────┘
                   ▼                                   ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  4. HITL + IMMUTABLE AUDIT TRAIL                                           │
   │     every decision: input · model_version · score · top SHAP · agent tool │
   │     calls · action · confidence · reviewer · timestamp · override flag     │
   └──────────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  EXPLANATION (cross-cutting): SHAP tuples + retrieved policy → Claude →    │
   │  grounded reason code. Claude narrates ONLY provided facts (no invention). │
   └──────────────────────────────────────────────────────────────────────────┘
```

**Key design principles (each is a talking point):**
- **Deterministic rules run before the LLM** (Bumblebee pattern) → precision + auditability.
- **The agent only investigates the *borderline* band** → bounded cost, mirrors Good/Bad/**Grey**.
- **The LLM never overrides the score** → it explains and recommends within policy.
- **Explanations are grounded** in SHAP + retrieved policy → avoids the documented LLM *faithfulness-vs-plausibility* gap (say this out loud — it signals ML maturity).
- **Everything is logged and human-overridable** → the audit trail *is* the deliverable.
- **Features computed identically offline and online** → no train/serve skew (narrate the real-time architecture; don't build Kafka).

---

## 6. Data Strategy (leakage-safe by design)

No clean public Indian COD-RTO labeled set exists, so we use a **controllable synthetic generator grounded in real data** — and we are *transparent* that it's synthetic (the track rewards honesty).

1. **Synthetic COD order generator** (`src/data/generate_synthetic_cod.py`) — samples orders whose RTO label is drawn from a **causal** model of real drivers (COD flag, address completeness, pincode base-risk, buyer prior-RTO, order value, category, distance, first-time buyer, device/velocity rings). We control ground truth → we can measure precision/recall + FP-cost honestly with **no leakage**.
2. **Real grounding:** join to the open **All-India Pincode Directory** (data.gov.in / Kaggle, lat/long + delivery flag) so geo/serviceability features are real. ~29k pincodes.
3. **Real-data validation (optional):** replicate the feature logic on **Olist** (real e-commerce; `order_status` → RTO-like label proxy) to show the pipeline works on real orders.

**The leakage discipline (our differentiator — do this exactly):**
- **Time-based split** (train on earlier orders, test on later) — never random shuffle for temporal data.
- **Out-of-fold / target-encoded** pincode-risk and buyer-history features — computed only from *training-fold* history, so the label never leaks into its own feature. This is *the* reason we beat the "0.99 AUC" toy models.
- **Test set keeps the natural fraud/RTO rate** (never resample the test set).
- **Any resampling (SMOTE/class-weights) happens inside the CV pipeline on the training fold only** — via `imblearn.Pipeline`.
- **Probabilities calibrated** (isotonic) on held-out data so the cost math is valid.

---

## 7. ML & Evaluation Spec — the crown jewel

**Model:** **LightGBM** primary (fast, tabular-native, SHAP-friendly), XGBoost as a documented comparison. Handle imbalance with `scale_pos_weight`/class weights first, SMOTE only if it demonstrably helps in-fold. **Calibrate** with isotonic regression.

**Anomaly layer (defense-in-depth, v2):** an unsupervised **Isolation Forest** runs *alongside* the supervised model. It flags orders that are statistically far from the manifold of normal commerce even when they carry **no fraud label** — catching zero-day tactics and cold-start buyers. This gives a two-tier "supervised + unsupervised" ensemble story that is cheap to build and strengthens the defensive posture. Its score is a feature/override signal, not a replacement for the calibrated GBM.

**The evaluation notebook** (`notebooks/03_evaluation.ipynb`) is what wins the grade. It must contain, in order:
1. **Why accuracy is banned** — state that "never-RTO" scores ~99% accuracy while catching zero. Never headline accuracy.
2. **PR-AUC as primary**, plotted against the **prevalence baseline** (horizontal line at positive rate) so the lift is honest and visible.
3. **ROC-AUC as secondary only**, explicitly noted as optimistic under imbalance.
4. **precision@k** and **recall@fixed-precision** — mirrors a fixed-capacity review queue.
5. **Calibration (reliability) curve** — proves probabilities mean what they say.
6. **The cost model** (assumptions written on the slide):
   - `c_FN` (missed RTO) = logistics loss (₹450–900) + at-risk item margin.
   - `c_FP` (blocked good order) = lost sale margin + CX/servicing + CLV slice.
   - Confusion matrix **translated into rupees.**
7. **Bayes Minimum Risk (BMR) cost-vs-threshold curve** (formalize it — Elkan's cost-sensitive framework): the expected loss of a decision is `L(x,i) = Σ_j P(j|x)·C(i,j)`; we predict the class minimizing expected cost. Concretely: `C(τ) = c_FP·FP(τ) + c_FN·FN(τ)`, sweep τ, mark the cost-minimizing **τ\*** (the BMR-optimal threshold), show it sits **far from 0.5** (≈ `c_FP/(c_FP+c_FN)`), and state the decision rule `Predict-flag if P(RTO|x) > τ*`. Report final cost **once** on the untouched test set. Naming it "BMR / Elkan" (not just "a cost curve") signals real ML-evaluation discipline.
8. **Honesty section**: the explicit no-leakage statement + a side-by-side with a *deliberately leaky* model to show how much AUC inflates — and a naïve "block-all-COD" baseline to prove our lift is real.
9. **Failure-Mode Transparency matrix** (v2): a table that names *where the model fails* (e.g., "sophisticated ring that rotates devices," "genuine buyer in a high-RTO pincode") and the **specific false-positive / false-negative rupee cost** each failure incurs. This literally answers the "no cherry-picked numbers" mandate — we volunteer our weaknesses before a judge asks.

> **This single notebook, plus the BMR cost curve and the failure-mode matrix, is the highest-leverage artifact in the whole project. Spend real time here — it is your ML strength and it is the literal rubric.**

---

## 8. Agentic Decisioning Spec

**Stack:** Claude Agent SDK (Python). **Models:** Opus 4.8 for the investigation agent (hard reasoning), Sonnet 4.6 as the fast workhorse for reason-code generation. (Latest models; Haiku 4.5 for any high-volume cheap calls.)

**Flow (only the AMBER/borderline band hits the agent):**
1. **Planner** inspects the order + band and picks which checks to run (skip expensive checks on obvious cases → bounded cost).
2. **Typed tools** (each returns structured data, each logged):
   - `get_buyer_history(buyer_id)` · `check_address_quality(address)` · `get_pincode_risk(pincode)` · `check_velocity(device_id, phone)` · `search_policy(query)` (RAG over the policy doc).
3. **Analyzer** runs deterministic rules → reads model score + SHAP → synthesizes → emits **structured JSON** (Pydantic-validated), never free prose:
   ```json
   {
     "order_id": "...", "risk_score": 0.63, "band": "amber",
     "action": "step_up_verification",
     "action_detail": "send COD-confirmation OTP; offer prepaid link with ₹50 nudge",
     "confidence": 0.71,
     "top_factors": [{"feature": "pincode_rto_rate", "impact": "+", "value": 0.34}, ...],
     "reason_code": "Elevated because delivery pincode has 34% historical RTO and address is missing a landmark; buyer is first-time on COD.",
     "policy_citations": ["RTO-POL-3.2 amber step-up", "RTO-POL-4.1 COD→prepaid"],
     "stopping_rule": "max 2 nudges over 48h then auto-cancel",
     "requires_human": false
   }
   ```
4. **Bounded action space** (defense-only): `approve` · `step_up_verification` · `convert_cod_to_prepaid` · `hold_for_review` · `escalate_to_human`. Nothing else is possible.
5. **HITL:** a human can override any recommendation; the override (reviewer, timestamp, reason, before/after) is logged.
6. **Stopping rules & compliance:** max N nudges, quiet-hours, then stop — no harassment (the track's "bounded" + "graceful" theme).

**Grounding guardrail (say this in the pitch):** the reason-code prompt gives Claude *only* the SHAP tuples + retrieved policy text and instructs it to narrate strictly those — no invented reasons. This directly addresses the faithfulness-vs-plausibility problem.

---

## 9. Tech Stack (with rationale + fallback)

| Layer | Choice | Why | Fallback |
|---|---|---|---|
| ML / eval | Python, pandas, **LightGBM**, scikit-learn, **SHAP**, imbalanced-learn, matplotlib | Your strength; tabular-native; explainable | XGBoost |
| Serving API | **FastAPI** + Pydantic + uvicorn | Typed, fast, Python-native | Flask |
| Agent | **Claude Agent SDK** (Python) | Mirrors Razorpay; native tools + structured output + approval gating | Direct Anthropic SDK w/ tool-use |
| RAG | **ChromaDB** + `sentence-transformers` (MiniLM) over the policy doc | Simple, local, shows real RAG | Keyword/BM25 |
| Store / audit | **SQLite** via SQLModel | Zero-infra, immutable append log | JSON lines |
| Dashboard | **Next.js + Tailwind + shadcn/ui + Recharts** (I scaffold ~all of it) | Looks like a real product; demo is the #1 driver | **Streamlit** (Python-only) if web debugging eats time |
| Packaging | **Docker Compose**, `.env.example`, seed data | One-command run for judges | `make` scripts |

**Decision:** we build the **Next.js dashboard** (industry-grade look, since the demo drives the outcome and I generate the frontend for you), with **Streamlit kept as a documented Plan B** for the analyst-review UI if time gets tight. You own Python; I own the JS.

**One external dependency to sort Day 1:** an **Anthropic API key** for the Claude Agent SDK (set in `.env`). Everything else runs locally/offline.

---

## 10. Demo & UI Spec (the golden path)

A rehearsed, hardcoded-safe **single flow** judges watch in the first 30 seconds:

1. **Hero / queue view** — a live queue of incoming orders with risk bands (green/amber/red) and rupee-at-risk.
2. **Click one AMBER order → case detail:**
   - risk score + **SHAP waterfall** (top factors),
   - **Claude reason code** (grounded),
   - **agent investigation trace** (tools called, policy citations),
   - the **recommended bounded action** + confidence + stopping rule.
3. **Human override** → logged to the **audit trail** view (show the immutable record).
4. **Threshold slider** — drag it and watch **precision / recall / ₹-cost** update live, with τ\* marked. *This is the "honest metrics + false-positive cost" moment, made interactive.*
5. Show a **red** order auto-held and a **green** order sail through frictionless (proves the tiering is real).

Keep a **screen-recording fallback**. Cache Claude responses for the demo path so a network blip never breaks it.

---

## 11. Repository Structure

```
axiom/
├── README.md                  # industry-grade: problem→demo→GIF→arch→metrics→run
├── PLAN.md                    # this file
├── docs/
│   ├── architecture.md        # + the diagram (exported PNG)
│   ├── evaluation.md          # the honest-metrics writeup
│   └── policy/rto_cod_risk_policy.md   # rules + RAG knowledge base
├── data/                      # generated CSVs (seed committed, large gitignored)
├── notebooks/
│   ├── 01_data_and_eda.ipynb
│   ├── 02_features_and_model.ipynb
│   └── 03_evaluation.ipynb    # ★ the crown jewel
├── src/
│   ├── data/generate_synthetic_cod.py
│   ├── features/build_features.py        # leakage-safe (OOF) encoders
│   ├── model/train.py  model/calibrate.py  model/explain_shap.py
│   ├── rules/decision_core.py            # deterministic rules + banding
│   ├── agent/tools.py  agent/investigate.py  agent/reason_code.py
│   ├── rag/index_policy.py  rag/retrieve.py
│   ├── audit/store.py                    # SQLite immutable log
│   └── api/main.py                       # FastAPI
├── web/                       # Next.js dashboard (scaffolded)
├── tests/                     # pytest: rules, cost-metric, no-leakage guard
├── requirements.txt  .env.example  .gitignore  docker-compose.yml
```

---

## 12. 13-Day Execution Plan (solo, all-in) — Aug 23 → Sep 5

| Day | Date | Deliverable |
|---|---|---|
| **1** | Aug 23 | ✅ Plan + repo skeleton + policy doc + **synthetic data generator** + get Anthropic API key |
| **2** | Aug 24 | Finish generator; join real pincode data; EDA notebook; design leakage-safe features |
| **3** | Aug 25 | Feature pipeline (OOF encoders); **time-based** train/val/test split; baseline LightGBM |
| **4** | Aug 26 | Model tuning + **calibration** + imbalance handling; SHAP explanations working |
| **5** | Aug 27 | ★ **Evaluation notebook**: PR-AUC, precision@k, cost model, **cost-vs-threshold curve**, leakage & baseline comparisons |
| **6** | Aug 28 | FastAPI scoring service + **deterministic rules/banding** + tiered action logic + **SQLite audit store** |
| **7** | Aug 29 | Claude Agent SDK: typed signal tools + planner + **structured JSON decision** + grounded reason codes |
| **8** | Aug 30 | **Policy RAG** (Chroma) wired into agent; HITL override flow; agent tool-calls logged to audit |
| **9** | Aug 31 | Next.js dashboard: order queue + **case-detail** view (score, SHAP, reason, agent trace, citations, action) |
| **10** | Sep 1 | Dashboard: **live threshold slider** (precision/recall/₹) + audit-log view + human override; wire to API |
| **11** | Sep 2 | End-to-end **golden-path** integration + polish; **Dockerize**; seed data; reproducibility check |
| **12** | Sep 3 | **Industry-grade README** + architecture diagram + metrics writeup; **record fallback demo**; bug buffer |
| **13** | Sep 4 | **5-min pitch video**; final QA; dry-run submission |
| — | **Sep 5** | **Submit early** (2–3 h buffer) |

**Buffer built in:** Days 11–13 are polish/pitch, so slippage in the build doesn't threaten submission. If a day slips, cut a *stretch* item (Section 15), never the eval or the golden path.

---

## 13. The 5-Minute Pitch Script

- **0:00–0:30 — Hook:** "False declines cost merchants ~13× more than fraud, and 33% of shoppers never come back after one. Yet risk teams get a black-box score with no *why*. On COD in India, RTO runs 20–40% — Razorpay lives this problem." 
- **0:30–1:15 — The gap:** opaque score + no explanation + slow manual review + no audit trail.
- **1:15–4:00 — Live demo (the core):** one amber order flows through → score → SHAP → **Claude reason code** → **agent gathers signals + RAG-checks policy** → **bounded recommendation + confidence + stopping rule** → **human override logged to audit trail**. Then drag the **threshold slider** to show precision/recall/₹ and τ\*.
- **4:00–4:30 — Architecture + why Claude:** the Bumblebee-style multi-agent shape, rules-before-LLM, grounded explanations, why we mirror Razorpay's own stack.
- **4:30–5:00 — Honest metrics + next steps:** PR-AUC vs baseline, the cost curve, the leakage-avoidance story; realistic roadmap. No overclaiming.

*Best mic. No sped-up audio. Public link. Uploaded 2–3 h early.*

---

## 14. Risk Register / Anti-Overscoping (solo discipline)

| Risk | Guardrail |
|---|---|
| **Overscoping (the #1 killer)** | ONE golden-path demo. Everything else is stretch. Cut features, never the eval. |
| Web debugging eats days | Streamlit Plan B ready; I generate all JS; keep UI stateless + simple |
| Live demo breaks | Cache Claude responses on demo path; screen-recording fallback recorded Day 12 |
| Building real-time infra | **Don't.** Narrate Kafka/Flink with a diagram; features are offline==online |
| Full GNN rabbit hole | Use cheap graph-*derived* features (shared device/phone fan-out); GNN is stretch only |
| API key / cost | Cache aggressively; use Sonnet/Haiku for cheap calls; Opus only for the investigation |
| Label leakage embarrassment | The no-leakage discipline (Section 6) is a *feature* we showcase, not a footnote |

---

## 15. Stretch Goals (only if ahead of schedule — never at the expense of the core)
Ordered by value-per-hour. Each is a *differentiator demo*, not a load-bearing dependency.
- **Graph-Sequential module (TRUST-inspired)** — a lightweight **Heterogeneous GNN** (PyTorch Geometric) over user↔device↔address↔pincode edges to catch fraud *rings* and cold-start "guilt by association," optionally fused with a small **Transformer sequence encoder** over the buyer's action timeline. This is the SOTA the real [TRUST framework (AAAI, deployed in Indian e-com)](https://ojs.aaai.org/index.php/AAAI/article/view/41450) uses. ⚠️ Full HGNN+Transformer is a **solo-killer in 13 days** — build it only if the core is done and rehearsed. (The *cheap graph-derived features* — shared-device/address fan-out, connected-component risk — are already promoted to the **core** feature set; they give ~80% of the value.)
- **Differentially-Private variant (DP-SGD / Opacus)** — a small PyTorch MLP trained with per-sample gradient clipping + calibrated noise, **reporting the privacy budget ε**, shown as a "privacy-preserving, membership-inference-immune" variant. Strong fintech-maturity signal. ⚠️ Keep LightGBM as the primary model — DP degrades accuracy and only wraps neural nets. (See §17 for the honest scoping.)
- A second **payment-fraud rail** on IEEE-CIS (same BMR-cost-curve architecture) + the **ROI = CP + CNP_LA + CNP_HA − LI** chargeback ROI decomposition → a unified "AI Risk Manager."
- A **Dispute Responder** mini-module (assemble chargeback-defense evidence) → nods to their revenue-ops roadmap.

---

## 16. Open Items to Verify (do Day 1)
- [ ] **Is the built project submitted *with* the application (by ~Sep 5) or only after shortlisting?** (decides final crunch) — check the Google Form.
- [ ] Confirm exact **deadline** on the form (announcements say Sep 5).
- [ ] Confirm **solo is allowed** / any team rules.
- [ ] Get the **Anthropic API key** into `.env`.
- [ ] Confirm any **submission format** requirements (repo link + video link + architecture doc).

---

## 17. v2 Enhancements (merged from the deep-research PDF)
*Provenance: these upgrade the plan with genuinely additive ideas from the "State-of-the-Art AI Risk Management" research. Where they modify earlier sections, this section is authoritative.*

**A. Cost-sensitive eval → Bayes Minimum Risk (BMR / Elkan).** Merged into §7 — formalize the cost curve as BMR, cite Elkan, state the decision rule. Framing/credibility upgrade.

**B. Unsupervised anomaly layer (Isolation Forest).** Merged into §7 — supervised GBM + unsupervised anomaly = defense-in-depth, catches zero-day/cold-start.

**C. Address Quality Score (upgraded verifier).** Replace the flat "address completeness" feature with a richer **Address Quality Score**: (1) cheap heuristics (length, missing house-no/landmark, pincode-format sanity, pincode↔city consistency) + (2) a **free-LLM (Gemini) check** that flags "monkey-typed" gibberish, missing landmarks, and address↔pincode mismatch, returning a 0–1 score + reasons. This is a *meaningful, cheap* use of the LLM that also powers the reason code, and it directly attacks the #1 RTO driver (bad checkout addresses). Optional geospatial polish: H3-cell / lat-long distance-to-warehouse. Inspired by the GeoIndia Seq2Seq geocoding approach — we approximate it with an LLM, no training needed.

**D. Dynamic Friction + Part-Pay COD.** Merged into §2 and the policy doc — adopt the "Dynamic Friction" name and add a **part-pay deposit (5–10% upfront via UPI)** action ("skin in the game") to the bounded action space. It's the sharpest way to *manage* false-positive cost rather than eat it.

**E. Failure-Mode Transparency matrix.** Merged into §7 (step 9) — volunteer where the model fails + the rupee cost, satisfying "no cherry-picked numbers."

**F. Defensive AI & Privacy-by-Design.** Two tiers:
- **In core (free, always):** data minimization; **no PII or protected attributes as features**; aggregate/derived features only; immutable audit; the model scores/flags/verifies but never generates or evades. This *is* our "strictly defense-only" evidence and it costs nothing (see policy RTO-POL-8).
- **Stretch differentiator:** a **DP-SGD (Opacus)** variant reporting ε (§15).
- **Honest scoping (important):** the PDF frames DP-SGD as *required* to satisfy "defense-only." We disagree, and say so: "defense-only" means *no offense-capable tooling* (no evasion/fraud-generation), which our system inherently satisfies. DP is a **bonus** that proves the model can't be inverted to leak training identities — a nice-to-have that trades accuracy, so it stays **off the primary LightGBM model** and appears only as a labeled privacy-preserving demo. Overclaiming DP as mandatory would itself be dishonest — and this track grades honesty.

**G. Graph-Sequential SOTA (TRUST/HGNN+Transformer).** Cheap graph features → core; full HGNN+Transformer → scoped stretch with the TRUST citation (§15).

### What we deliberately did NOT adopt as core (and why)
- **Full HGNN + Transformer as the primary model** — overscope for a solo 13-day build; we capture most of its value with cheap graph features and keep it as a roadmap/stretch demo.
- **DP-SGD replacing LightGBM** — Opacus needs a neural net, DP hurts accuracy, and our metrics *are* the grade. DP stays a scoped demo.
- **IEEE-CIS as the primary dataset for RTO** — it's card fraud, not RTO; our leakage-safe synthetic COD generator is the right primary. IEEE-CIS feeds the stretch payment-fraud rail.

### SOTA references worth citing in our repo (from the PDF)
Elkan cost-sensitive learning · Bahnsen example-dependent cost trees · [TRUST (AAAI)](https://ojs.aaai.org/index.php/AAAI/article/view/41450) · [Opacus DP-SGD](https://opacus.ai/) · GeoIndia geocoding · Razorpay Thirdwatch ML blog.

---

## Definition of Done (the winning checklist)
- [ ] Public repo, **one-command run** (`docker compose up`), seed data included.
- [ ] README: problem (1 line) → demo link → GIF → architecture → **honest metrics** → run steps.
- [ ] Detector + **verifier** + **auto-responder** all demonstrably present.
- [ ] Evaluation: PR-AUC vs baseline, precision@k, calibration, **rupee cost-vs-threshold curve with τ\***, leakage statement.
- [ ] Claude agent: typed tools, RAG policy citations, **structured decision**, grounded reason codes.
- [ ] **HITL + immutable audit trail** visible in the UI.
- [ ] **Defense-only** stated; no offense-capable anything.
- [ ] Rehearsed 5-min video, golden path, fallback recording.
- [ ] Every claim honest; one stated limitation.

**Remember: depth on the eval + alignment with Razorpay's architecture. That is the whole game.**
