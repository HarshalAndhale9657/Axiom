# Axiom v3 — Upgrade Plan ("make it undeniably real")

Goal: eliminate the *"is this a toy on dummy data?"* doubt and showcase advanced, **bounded, honest** agentic properties — without breaking the $0 / defense-only / honesty-graded constraints. Every item below has a **honesty guardrail** and an **acceptance criterion**. Nothing ships that we can't defend to a skeptical Razorpay judge.

## Principles (non-negotiable)
- **Honesty-first.** Every number is one we actually ran; every borrowed stat is attributed as external/directional; synthetic-vs-real provenance is always labelled in the UI.
- **Free-first, provider-agnostic.** Gemini free tier is primary; everything degrades to deterministic. OpenAI ($3) is used only for the cross-vendor verifier (optional).
- **Defense-only.** Scores/flags/verifies/protects. Real actions (payment links, verification messages) protect the buyer + merchant; never punitive, never offense-capable.
- **Small, tested, reversible commits.** Each item lands green with tests.

---

## Finalized scope

| Build now (IN) | Skip unless time |
|---|---|
| A1 Real pincode grounding · A2 Olist real validation · A3 Provenance badge + datasets manifest | Supervised GNN (torch fragile; may not beat LightGBM; ring graph gives ~80% of the wow) |
| B1 **Real Razorpay test payment link** · B2 **Fraud-ring graph** · B3 **Leaky/honest toggle** | DP-SGD variant (lowest honesty margin; DP-on-trees awkward) |
| C1 Autonomous batch mode · C2 Cross-vendor verifier · C3 Analyst copilot | 2nd real rail (IEEE-CIS payment fraud) |
| D1 SHAP waterfall · D2 Counterfactual what-if · D3 Merchant economics · D4 Model card | |
| E1 SSE live stream · E2 Real WhatsApp/SMS step-up · E3 Public deploy (optional) · F1 Hardening · F2 Pitch | |

## Provider & keys strategy
- **Primary LLM:** Gemini (free) for reason codes, agent, copilot.
- **Verifier (C2):** **OpenAI `gpt-4o-mini`** when `OPENAI_API_KEY` present → *independent, cross-vendor* second opinion (the honest multi-agent flex). Fallback: Gemini second-pass → deterministic. ~$3 covers thousands of demo calls.
- **Keys needed from the user:** free **Razorpay TEST key_id/secret** (B1 — free, no KYC), **OpenAI key** (have it, C2), optional **Twilio trial / Fast2SMS** (E2), **Kaggle** account for dataset pulls (free). All in `.env` (git-ignored); never `NEXT_PUBLIC_`.

## Milestones (suggested order; M1 needs no external keys)
- **M1 Realism foundation:** A1 → A3 → B3  *(fast, high-impact, no vendor keys)*
- **M2 The killers:** B1 (needs Razorpay test key) → B2
- **M3 Agentic depth:** C1 → C2 (OpenAI) → C3
- **M4 Explainability polish:** D1 → D2 → D3 → D4
- **M5 Real validation:** A2 (+ drift) 
- **M6 Liveness/reach:** E1 → E2 (needs Twilio/Fast2SMS) → E3 (optional)
- **M7 Ship:** F1 hardening + overclaim scrub → F2 pitch script + record demo

---

## Item specs

### A1 · Real Indian pincode grounding
- **Goal:** back `pincode`, `city_tier`, `is_serviceable`, `distance_km` with real Indian geography.
- **Build:** `src/data/real_pincode.py` builds a committed `data/pincode_lookup.parquet` (`pincode → lat, lon, district, state, is_serviceable, tier`); `generate_synthetic_cod.py` samples **real pincodes + real coordinates**; `scripts/fetch_real_data.py` pulls sources.
- **Data:** admin mapping (district/state/**Delivery** flag → serviceability) from the **OGD All-India Pincode Directory**; **coordinates from an open Kaggle mirror** (the OGD file's lat/long is largely NA — *verify at build time*). Commit only the small aggregated lookup; gitignore raw dumps.
- **Tests:** lookup schema; coords in India bbox; serviceability present; generator emits real pincodes.
- **Honesty:** README/UI note "admin mapping from OGD; coordinates from an open Kaggle mirror (~19k delivery pincodes)"; don't claim data.gov.in provides coords.
- **Effort:** M · **Acceptance:** dashboard shows real pincodes/cities; distances computed from real coords.

### A2 · Olist real-order validation (the knockout to "toy data")
- **Goal:** run the *identical* leakage-safe pipeline on **99,441 real orders** and report the honest (lower) real metric + domain-shift table.
- **Build:** `src/data/olist_adapter.py` (map Olist → Axiom feature contract), `notebooks/04_real_validation.ipynb`, `src/monitor/drift.py` (PSI/KS).
- **Label (RTO-proxy):** primary = `order_status ∈ {canceled, unavailable}` (**~1.24%** positive — keeps a real minority base rate); optional broad = + delivered-late (`order_delivered_customer_date > order_estimated_delivery_date`, ~+7%). **Exclude in-flight statuses** (`created/approved/invoiced/processing/shipped`) — their outcome is censored. **Post-outcome fields (`order_status`, `order_delivered_*`, `order_approved_at`) are the label — never features.** Time-split on `order_purchase_timestamp`.
- **Tests:** adapter schema; label ∈ {0,1}; PSI function on a hand example; no post-outcome field in the feature set.
- **Honesty:** label everything **"RTO-proxy"**; Olist is **Brazilian, CC BY-NC-SA 4.0** → attribute Olist, non-commercial only; real PR-AUC **will** be lower → present the gap as domain shift, never massage; **recalibrate on a real held-out slice before any ₹ claim** on real data.
- **Effort:** L · **Acceptance:** notebook reports real PR-AUC vs baseline + a PSI/KS drift table; README "External validation" section.

### A3 · Provenance badge + datasets manifest
- **Build:** add `provenance` field (`synthetic` | `olist_real`) to the order/audit schema + `GET /provenance`; dashboard **provenance badge** + queue toggle (synthetic ↔ real); `docs/datasets.md` (link, license, rows, columns-used, label rule per dataset) + `scripts/fetch_real_data.py`.
- **Honesty:** tag every row's true provenance; a real Olist row's score is a **proxy-label** model output — tooltip says so; never render synthetic as real.
- **Effort:** S · **Acceptance:** first 30s of the demo shows a provenance badge and a real order flowing through the same pipeline.

### B1 · Real Razorpay test-mode payment link (the flagship "not-dummy" move)
- **Goal:** executing `convert_cod_to_prepaid` / `part_pay_cod` returns a **genuine** `https://rzp.io/i/…` link (+ `plink_…`, `order_…`) shown in case detail + audit.
- **Build:** `src/actions/razorpay_actuator.py` — `pip install razorpay`; `client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))`.
  - `create_prepaid_link(order)` → `client.payment_link.create({...})`. **`amount` in PAISE** (`int(order_value*100)`), `currency:"INR"`, `description`, `customer{name,contact,email}`, `notify{sms,email}`, `reminder_enable`, `notes{axiom_risk_score, band, rule_id}`, `reference_id=order_id` (unique). Response → store `id` (`plink_`), `short_url`, `status`.
  - `create_partial_link(order, deposit_inr)` → same with `accept_partial:True`, `first_min_partial_amount:int(deposit_inr*100)`; `deposit_inr` computed from the **BMR cost curve** (the deposit that neutralises expected RTO loss at that band).
  - `create_order(order)` → `client.order.create({amount, currency:"INR", receipt:order_id[:40], notes:{...}})` (**receipt = idempotency key**); pin the returned `order_…` in audit.
  - `RAZORPAY_ENABLED` env-flag; **stub/offline mode** returns a clearly-labelled simulated link when keys absent.
  - `POST /orders/{id}/execute` runs the actuator for the recommended action; audit records the real ids.
- **Stretch B1b · webhook:** `POST /webhooks/razorpay` — read **raw body**, header `X-Razorpay-Signature`, `client.utility.verify_webhook_signature(raw, sig, secret)`; on `payment_link.paid` → resolve the case (risk neutralised: buyer paid) + immutable audit row. Tunnel with cloudflared/ngrok for the demo.
- **Tests:** payload builder (amount in paise, correct fields) with a **mocked** client; stub mode returns a simulated link; action→actuator mapping; audit stores ids. **No live API in tests.**
- **Honesty:** UI/README: *"REAL Razorpay test-mode link — no real money moves."* Badge shows "REAL Razorpay test-mode" **only** when a real `rzp.io` `short_url` was returned; else "simulated (offline)". Never imply live-mode/settlement. Disclose the sandbox caveat (a dummy payment may not complete in checkout — the *link* is real).
- **Effort:** M (link) + M (webhook) · **Needs:** Razorpay test keys · **Acceptance:** clicking "Execute" on a convert/part-pay action yields a real clickable `rzp.io` link + ids in audit.

### B2 · Interactive fraud-ring graph (crown jewel, unsupervised)
- **Goal:** surface shared-device/phone/address rings via community detection — **with zero label access** — then honestly validate against the hidden `_is_ring` latent.
- **Build:** `src/graph/rings.py` (`networkx` + `python-louvain`): bipartite `device↔buyer` (+ optional pincode co-location) → projected entity graph (edge = shared device); connected components + Louvain (fixed seed); `ring_risk = f(distinct buyers/device, order velocity/burstiness, mean address_completeness, COD share, new-account share)`. `GET /rings`, `GET /rings/{id}`. Dashboard `RingGraph` via `react-force-graph-2d` (dynamic import, `ssr:false`); clicking a queue order highlights its ring + neighbours. Eval: in `notebooks/`, score discovered high-risk components vs `_is_ring` from `*_latents.csv` → **honest precision/recall/lift**.
- **Tests:** graph builds from orders; ring_risk deterministic (seed); **guard: construction never reads `is_rto`/`_is_ring`**; benign vs suspicious clusters separated.
- **Honesty:** on-screen "topology only — never the label"; benign family/repeat-buyer clusters shown in a different colour and **not** called fraud; Louvain seed fixed & disclosed; claim "surfaces shared-identity clusters for review", not "catches fraud in production".
- **Effort:** L · **Acceptance:** interactive ring graph tab; clicking a ring order highlights its component; notebook reports honest ring precision/recall.

### B3 · Live "Leaky vs Honest" toggle (weaponize the 0.51)
- **Goal:** show a deliberately **leaked** model (~0.97 ROC-AUC) beside Axiom's honest **0.80**, proving we can build the fake 0.99 and chose not to.
- **Build:** `build_features.py` gains a `leak=True` path (fit pincode/buyer encoders on **all** rows, no OOF; include the row's own label in buyer prior); `train.py` trains the leaky variant; precompute **both** metric sets to `data/leak_compare.json`; Economics tab toggle; a "Leakage tax" cell in `03_evaluation.ipynb`.
- **Tests:** leaky AUC ≫ honest AUC (the leak is real); honest path unchanged; **test set stays untouched/natural-rate in both** (fair comparison).
- **Honesty:** the leaky model is labelled **"INVALID — illustration only"** everywhere; caption explains *why* it's a lie.
- **Effort:** S · **Acceptance:** the toggle flips the metrics live with the explanatory caption.

### C1 · Autonomous batch mode ("money recovered across a batch")
- **Goal:** the agent works the whole AMBER queue autonomously with stopping rules and reports **measured ₹ recovered across a batch**.
- **Build:** `src/agent/batch.py` (iterate amber orders; per-order investigate; **stopping rules**: max-N/run, budget cap, stop after K consecutive low-value, quiet-hours respected); aggregate ₹ recovered = prevented-RTO cost on orders it flagged that *would* have RTO'd (measured post-hoc vs `is_rto` on the **labelled test batch**). `POST /batch/run` + progress; dashboard "Batch" view with live tally + actions log.
- **Tests:** stopping rules fire; ₹ tally math on a tiny example; every batch decision audited.
- **Honesty:** "₹ recovered measured on a labelled held-out test batch" (disclosed); stopping rules are real; never spam (reuses policy RTO-POL-5 limits).
- **Effort:** M · **Acceptance:** "Run batch" processes the queue, shows ₹ recovered + actions + stop reason; all in audit.

### C2 · Cross-vendor adversarial verifier
- **Goal:** an *independent* model second-checks the agent's decision (agree / veto), from a **different vendor**.
- **Build:** `src/agent/llm.py` gains `OpenAIProvider` (gpt-4o-mini). `src/agent/verify.py`: given the primary decision + evidence + retrieved policy, an independent agent judges *is this action appropriate & grounded?* → `{verdict: agree|veto, reason, confidence}`. `investigate.py`: run the verifier (OpenAI if key, else Gemini second-pass, else skip); on **veto/disagree** → escalate_to_human or drop confidence; audit both opinions.
- **Tests:** agree/veto paths (mock); veto → escalate; provider-selection logic; graceful skip when no key.
- **Honesty:** UI says which model verified (e.g., "verified by gpt-4o-mini — independent vendor"); if same vendor, say "second-pass (same model family)" — don't overclaim independence.
- **Effort:** M · **Needs:** OpenAI key · **Acceptance:** case detail shows a named independent verifier verdict; a veto escalates.

### C3 · Grounded analyst copilot
- **Build:** `src/agent/copilot.py` (system grounds strictly on the case JSON + policy RAG + SHAP factors; answers only from provided context, may say "not in the record"); `POST /orders/{id}/ask`; chat box in CaseDetail.
- **Tests:** answers reference provided factors/policy; refuses ungrounded questions (mock).
- **Honesty:** grounded-only; no free-roaming claims.
- **Effort:** M · **Acceptance:** "why flagged? what if the buyer verifies?" → grounded, cited answers.

### D1 · SHAP waterfall visual
- Recharts diverging/running-total bar in CaseDetail from `top_factors` + model base value; log-odds axis labelled honestly (isotonic is monotone → ordering/sign faithful). **Effort S.**

### D2 · Counterfactual "what-if" recourse
- `src/model/counterfactual.py`: bounded grid over **actionable-only** features (`address_completeness`, `phone_verified`, `is_cod`→convert, part-pay) → minimal change that crosses τ*; CaseDetail before/after bar tied to the recommended action. **Honesty:** vary only what a buyer/merchant can change; say "the model would score X", not "prevents the return". **Effort M.**

### D3 · Per-merchant economics on the cost slider
- Parameterize the cost curve by `(margin, c_FP, c_FN)` presets (thin-margin fashion vs high-margin electronics); recompute τ* = c_FP/(c_FP+c_FN) + rupee matrix client-side; plain-language ₹ readout. **Honesty:** cost assumptions shown on-screen as illustrative; the 13× stat attributed (Javelin 2021, directional). **Effort S/M.**

### D4 · Model Card + provenance/reproducibility
- `MODEL_CARD.md` (Google/HF/EU-AI-Act structure: intended/out-of-scope use, data provenance + seed, leakage-safe method, eval, failure-mode matrix, defense-only, **genuine limitations**); `GET /model_meta` (model_version, seed, train window, feature manifest, "no PII/protected attributes" badge, calibration date). **Effort S.**

### E1 · Live SSE order stream
- `sse-starlette` `GET /stream` replays the held-out test split (~1.5s/order) with the existing `queue_view()` payload; Next.js `EventSource` prepends rows + a pulsing **LIVE** badge. **Honesty:** banner "replay of held-out test orders the model never trained on" (truthful and *stronger*). **Effort M.**

### E2 · Real WhatsApp/SMS step-up (the judge's phone buzzes)
- `src/actions/notifier.py` (Notifier protocol; `TwilioWhatsApp` sandbox + `Fast2SMS` + `mock`; `AXIOM_NOTIFIER` env). `POST /orders/{id}/verify` sends a real "confirm your COD order — reply YES" message; inbound webhook `POST /webhook/verify` (reply YES → approve + immutable audit, reusing the override machinery). **Honesty:** disclose Twilio sandbox join-keyword/24h window (pre-join the demo phone) or Fast2SMS test credit (finite); verification = "customer confirmed intent", not KYC. **Effort M · Needs:** Twilio trial or Fast2SMS.

### E3 · Public live URL (optional, final)
- Vercel (Next.js) + Render (FastAPI with model baked in) + a 5-min keep-warm ping. **Honesty:** free-tier, non-commercial (Vercel Hobby), cold-start disclosed; keys server-side only; Gemini/verifier stay on-demand (not in the hot stream path). **Effort L.**

### F1 · Hardening + overclaim scrub
- `DEMO_MODE` cache: agent returns stored traces for demo order_ids (live path otherwise) so a network blip never stalls the stage demo; deterministic DB seed; 6-step click runbook + a "wrong click" recovery; fallback screen-recording. Grep the repo/UI for `powered`/`production`/`best`/`%` → replace with cited, hedged phrasing; add a "What this is NOT" block. **Honesty:** disclose caching if asked ("cached for demo reliability; here's the live call"). **Effort S/M.**

### F2 · 5-minute pitch script
- Golden-path narration mapped beat-by-beat to Track-2's rubric (hook → live demo → honest metrics → bounded/defensive → close). **Effort S.**

---

## Cross-cutting honesty rules (apply to every item)
1. Provenance is always visible (synthetic vs real; live vs cached; test-mode vs prod).
2. No metric shown that we didn't run; external stats attributed as directional.
3. Real actions are defense-only and buyer-protective; disclose sandbox/test constraints.
4. Every new model/agent path has a deterministic fallback and is auditable.

## Risk register
| Risk | Mitigation |
|---|---|
| Razorpay/Twilio/OpenAI key or free-limit issues | Env-flagged; stub/offline modes; deterministic fallbacks; disclose limits |
| torch-geometric / DP install fragility on Windows | Both are SKIP; the unsupervised ring graph needs no torch |
| Live-demo network failure | `DEMO_MODE` cached traces + recorded fallback |
| Overclaiming (dishonest → fails the grade) | Per-item honesty guardrail + F1 overclaim scrub |
| Pincode coordinate source (OGD coords NA) | Use Kaggle lat/long mirror; verify at build; note provenance |
| Olist license (CC BY-NC-SA) | Attribute Olist, non-commercial demo only, label RTO-proxy |

## Updated Definition of Done (v3)
Real pincode geography · Olist real-validation with honest lower metric + drift table · a real Razorpay test link produced live · honestly-validated fraud-ring graph · leaky/honest toggle · cross-vendor verifier + autonomous batch ₹-recovered + grounded copilot · SHAP waterfall + counterfactual + merchant economics · model card + provenance · (live stream / phone / deploy as reach) · all tests green · overclaims scrubbed · rehearsed 5-min video.
