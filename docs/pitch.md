# The 5-minute pitch — beat sheet

Target **4:45**, leaving buffer. Rehearse it three times against a timer before recording.
Screen-record at 1920×1080, dashboard in **dark mode**, browser zoom 90%, API already warm.

**The single idea the judges should remember:**
> *Blocking all COD costs more than approving everything. Axiom is the system that proves that in rupees and then acts on it — bounded, auditable, and honest about what it gets wrong.*

---

## Before you hit record

- [ ] `uvicorn src.api.main:app` running and **warmed** — load `/metrics`, `/baselines` and `/slices` once; the ablation trains two models on first call and you do not want that latency on camera.
- [ ] `npm --prefix web run dev` running; dashboard open on the **Risk Queue** tab.
- [ ] `.env` has `GEMINI_API_KEY` (and `OPENAI_API_KEY` for the cross-vendor verifier). Check the free-tier quota is not exhausted — if it is, the deterministic fallback shows and you must say so on camera rather than hide it.
- [ ] A terminal open at the repo root, font size up, ready to run `pytest -q`.
- [ ] Close every notification. One take, no cuts if you can manage it.

---

## 0:00 – 0:35 · The problem, in one number

> "Cash on delivery is 60% of Indian e-commerce, and roughly a quarter of those orders come straight back — return to origin. The merchant eats the round trip twice.
>
> So the obvious fix is: stop taking COD from risky customers. I measured what that actually costs." *(Economics tab, point at the table.)*
>
> "Blocking all COD costs **₹71,776** per thousand orders. Approving everything — doing literally nothing — costs **₹64,795**. **The blunt fraud control is worse than having no fraud control at all**, because the friction you put on good customers is not free.
>
> That is the false-positive problem. It is what Track 2 asks you to measure, and it is what Axiom is built around."

**On screen:** Economics tab, the three-row cost table.

---

## 0:35 – 1:35 · The product, on one real case

*(Risk Queue tab. Click an amber order.)*

> "Every order gets a calibrated return-risk probability. Not a score out of 100 — a probability, because everything downstream is rupee arithmetic on it.
>
> Here is why this one is flagged." *(SHAP bars.)* "Incomplete address, tier-3 pincode, COD, first-time buyer. Those are SHAP attributions from the model — actual per-order factors, not a template.
>
> Green and red get an instant bounded action. **Only amber reaches the agent** — that keeps it fast and free." *(Click Investigate.)*
>
> "It runs typed tools — buyer history, address check, pincode risk, velocity — retrieves the matching clause from the risk policy, and returns a **schema-constrained** decision. It can only pick from six actions. It cannot invent a seventh, it cannot change the score, and it narrates only the SHAP factors it was handed.
>
> Then a **second model from a different vendor** — OpenAI checking Gemini — reviews that recommendation and can veto it. A veto escalates to a human." *(Point at the verifier verdict.)*
>
> "And the action is real." *(Click Execute.)* "That is a genuine Razorpay **test-mode** payment link. No real money moves, but the rail is real — the auto-responder is not a mock.
>
> Note what the action *is*: convert to prepaid. Not a ban. **Every action here is reversible**, because we know some of these customers are innocent."

**On screen:** case detail → SHAP → agent trace → verifier → real `rzp.io` link.

---

## 1:35 – 2:05 · Bounded, audited, overridable

*(Override the decision, then jump to the Audit tab.)*

> "I disagree with the agent, so I override it — and that override is logged with before and after and my name on it.
>
> This audit table is append-only, enforced by database triggers: `UPDATE` and `DELETE` are blocked at the storage layer, not by convention. Every decision, every agent call, every override.
>
> And when the LLM is unavailable or out of quota, the deterministic core takes over and the trace says `fallback` — it degrades honestly instead of failing."

**On screen:** audit trail with the before→after override row.

---

## 2:05 – 3:45 · The part that is actually being graded

*(Evidence tab. Slow down here. This is the section that wins or loses.)*

> "Track 2 says honest metrics including false-positive cost. So here is the evidence, and here is where I tried hardest to prove myself wrong.
>
> **One. The threshold was chosen without looking at the test set.** Everyone sweeps a cost curve and quotes its minimum — but if you sweep it on your test data, that minimum is an oracle you can never reach in production. Mine is fitted on **validation**, frozen at train time, and the test split is scored once. Tuning on test would have made my headline look **₹1,570 per thousand better**. That number is on the screen because I did not take it.
>
> **Two. I found a leak inside my own leakage-safe pipeline.** I already split by time and used out-of-fold encoding. But an order placed today cannot know whether *yesterday's* order was returned — the courier has not even attempted delivery. My history features were counting outcomes that had not happened yet. So every label-derived feature now waits **seven days**. It cost me 0.003 PR-AUC. I published the cost.
>
> **Three. I report the comparison I lose.** My LightGBM beats a hand-written expert scorecard clearly. Against a plain **logistic regression**, the paired bootstrap interval is minus-one to plus-one-point-seven — **it spans zero. I have not shown my model is better, and that is on the page.** I keep LightGBM for the interaction structure and for SHAP, and I say exactly that rather than implying an accuracy win I cannot defend.
>
> **Four. I name the good customers who pay for my false positives.** A genuine tier-3 buyer is **3.8× more likely** to be challenged than a tier-1 buyer. Fourteen percent of good ₹2k–5k orders get friction. That is a real cost to real people — and it is precisely why the response is *verify*, never *block*.
>
> Every number here has a confidence interval, and none of them is typed by hand." *(Cut to terminal.)* "One command regenerates the evaluation page, the figures and the JSON — and there is a **test that reads my README and fails if it disagrees with the measurements**."

**On screen:** Evidence tab, top to bottom → terminal running `python -m src.model.full_report --check`.

---

## 3:45 – 4:15 · The one everybody expects

*(Economics tab, leaky/honest toggle.)*

> "Public RTO models advertise 0.99 AUC. Here is that number, on my own data, in one line of code: **0.97 ROC-AUC** — by fitting the encoders on all rows including each row's own label.
>
> It is worthless. The model memorised the answer. My real number is **0.80**, and it is the one that survives contact with real orders.
>
> I built the impressive lie so I could show you why I did not ship it."

**On screen:** the side-by-side honest / INVALID toggle.

---

## 4:15 – 4:45 · Close

*(Terminal: `pytest -q` finishing, then the Fraud Rings tab for two seconds.)*

> "175 tests, including the leakage guards, the cost arithmetic, and the claim checks on the README. CI rebuilds the dataset and the model from scratch on every push and re-audits every published number.
>
> The dataset is **synthetic** — no clean public Indian COD/RTO data exists — and that is stated on every page, along with the cost assumptions and the action-efficacy assumptions I could not measure. The model card lists every limitation I know of.
>
> Axiom is defense-only: it scores, verifies and protects, and every action it takes can be undone.
>
> The pitch is not that I built the most accurate model. It is that **every number I have shown you is one I could defend in a review** — and on a system that touches money, that is the only kind worth having."

---

## Judge questions to have ready

| Question | Answer |
|---|---|
| *"Why is your AUC only 0.80?"* | Because it is real. The leaky variant hits 0.97 — I show it. RTO has irreducible noise: whether someone is home is not in the features. |
| *"Your data is synthetic — so what does this prove?"* | The methodology, which is what transfers. The generator's latents are hidden from the model, the metrics are measured on held-out data, and the pipeline runs unchanged on real orders after recalibration. I state it everywhere rather than burying it. |
| *"Why LightGBM if logistic regression matches it?"* | It does not *beat* it on this data and I say so. LightGBM handles the categorical and velocity interactions and gives per-order SHAP that the agent narrates. If a merchant's data showed the same tie, shipping the logistic model would be the right call. |
| *"Where do c_FP and c_FN come from?"* | They are assumptions, stated on-screen. The slider exists so you can substitute yours; the conclusion — that blocking all COD is worse than doing nothing — holds across the plausible range. |
| *"How do you know a step-up prevents a return?"* | I do not. It is the largest assumption in the band economics, so I sweep it: τ_low moves from 0.11 to 0.73 across plausible efficacies. The formula ships, not the constant. |
| *"What happens when Gemini is down?"* | Fail-over to OpenAI, then to the deterministic core. The trace labels which one served, and the verifier only claims cross-vendor independence when the vendors genuinely differed. |
| *"Could this be used offensively?"* | No. It scores and applies reversible friction. There is no evasion tooling, no fraud generation, and no irreversible action anywhere in the closed action set. |

---

## Cutting order if you run long

1. Fraud Rings tab (mention in one line instead).
2. The batch-mode tab (the audit trail already carries the bounded-agent story).
3. The copilot chat.

**Never cut:** the opening cost table, the Evidence tab, or the leakage toggle. Those three are the submission.
