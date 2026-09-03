# The 5-minute pitch — beat sheet

Target **4:45**, leaving buffer. Rehearse it three times against a timer before recording.
Screen-record at 1920×1080, dashboard in its default **light** theme (higher contrast on a
compressed video than dark), browser zoom 90%, API already warm.

**The single idea the judges should remember:**
> *Razorpay already grades COD risk. Axiom is the evidence layer that proves — in rupees, out-of-sample, with the break-even published — which grade is right and what being wrong costs.*

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
> Magic Checkout already grades this — nudge to prepay, differential COD fees, disable COD for repeat offenders. So I did not build another risk score. I built the evidence layer underneath it: the part that says which grade is right and what being wrong costs, in rupees." *(Economics tab, point at the table.)*
>
> "Here is why grading beats a binary block. Blocking all COD costs **₹71,776** per thousand orders. Approving everything — doing literally nothing — costs **₹64,795**. **The blunt control is worse than no control at all**, because the friction you put on good customers is not free.
>
> And that is a claim, not a measurement, so it ships with its break-even: it holds while challenging a genuine customer costs more than **₹123**. I assume ₹138. That is 1.12× headroom, and I would rather you saw the pivot than took my word for it."

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
> **Three. I report the comparison I lose — and I can explain why I lose it.** My LightGBM beats a hand-written expert scorecard clearly. Against a plain **logistic regression**, the paired interval spans zero: **I have not shown my model is better, and that is on the page.** The reason is not modesty, it is my own data — the generator builds risk as a weighted sum through a sigmoid, purely additive, so logistic regression is the *correctly specified* model and cannot be beaten here. I measured that instead of asserting it: adding all 231 pairwise interactions moves PR-AUC by minus-nought-point-nought-three-eight. There is nothing non-additive to find. Real order flow has interactions; my synthetic world does not, so I keep the tree and decline the claim.
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

> "178 tests, including the leakage guards, the cost arithmetic, and the claim checks on the README. CI rebuilds the dataset and the model from scratch on every push and re-audits every published number.
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
| *"You only catch a third of the returns."* | Deliberate, and I can price the alternatives. Recall 0.67 costs ₹1,753 more per 1k; recall 0.79 costs ₹5,714 more — past ~0.65 the friction outruns the returns prevented. But note the honest wrinkle: recall 0.53 would have been ₹1,570 *cheaper* on test. That is exactly my published optimism gap. Validation put τ at 0.315; taking the cheaper point requires knowing the test set, which is the one thing I will not do. |
| *"Why is your AUC only 0.80?"* | Because it is real. The leaky variant hits 0.97 — I show it. RTO has irreducible noise: whether someone is home is not in the features. |
| *"Your data is synthetic — so what does this prove?"* | The methodology, which is what transfers. The generator's latents are hidden from the model, the metrics are measured on held-out data, and the pipeline runs unchanged on real orders after recalibration. I state it everywhere rather than burying it. |
| *"Why LightGBM if logistic regression matches it?"* | Because the tie is an artefact of my own generator and I can prove it. The data-generating process is a sigmoid over a weighted sum — purely additive, no interaction terms — so logistic regression is the *correctly specified* model here. I measured it: adding all 231 pairwise interactions to the logistic model changes PR-AUC by −0.038. There is nothing non-additive to find. On real order flow there is (a first-time buyer at a bad pincode is worse than the sum), which is why I keep the tree — but I cannot demonstrate that on this data, so I do not claim it. If a merchant's real data showed the same tie, shipping the logistic model would be the right call. |
| *"Where do c_FP and c_FN come from?"* | They are assumptions, stated on-screen, and I publish the break-even rather than defending the point estimate. Block-all-COD stops being worse than doing nothing below ₹123 per challenged genuine customer; I assume ₹138. If your number is lower, my headline reverses and I would want to know that. The rest of the system — out-of-sample threshold, ranking quality, the slice audit — does not move. |
| *"How do you know a step-up prevents a return?"* | I do not. It is the largest assumption in the band economics, so I sweep it: τ_low moves from 0.11 to 0.73 across plausible efficacies. The formula ships, not the constant. |
| *"What happens when Gemini is down?"* | Fail-over to OpenAI, then to the deterministic core. The trace labels which one served, and the verifier only claims cross-vendor independence when the vendors genuinely differed. |
| *"Isn't this just Magic Checkout?"* | The action ladder is the same, and that is deliberate — you already proved graded response is right. What I add is the evidence layer: a threshold fitted out-of-sample with the optimism published, a break-even under every cost assumption, the per-slice bill genuine customers pay for false positives, and an audit trail that makes a decision defensible weeks later. I am not claiming a better score than yours. I am claiming I can show my working. |
| *"Your data is synthetic and your model recovers your own generator."* | Yes — that is the honest reading, and it is why the logistic tie happens. What transfers is the method, not the number: the leakage discipline, the out-of-sample threshold, the cost framing, the slice audit. The first thing I would want on real order flow is a recalibration and a fresh threshold fit; the second is to check whether the interaction structure I could not test for actually shows up. |
| *"Could this be used offensively?"* | No. It scores and applies reversible friction. There is no evasion tooling, no fraud generation, and no irreversible action anywhere in the closed action set. |

---

## Defend every design choice (rehearse these separately)

The repo is a stronger artifact than most people can defend live, and every choice in it is
a question the panel can ask. Have a two-sentence answer for each before adding anything new.

| Choice | Why, in two sentences |
|---|---|
| **Isotonic calibration, not Platt** | Platt assumes the miscalibration is sigmoidal; a GBDT's distortion is not, it is monotone but arbitrary. Isotonic fits any monotone map, and with 3,000 validation rows there is enough data that its extra flexibility does not overfit. |
| **No SMOTE / class weights** | At 17% positives this is moderate imbalance, not the sub-1% extreme where resampling helps ranking. Every downstream decision is a rupee threshold on a probability, and resampling distorts exactly those probabilities — I would gain nothing and break the cost arithmetic. |
| **IsolationForest as a trip-wire, not a feature** | As a feature it would be one more correlated input the GBDT mostly ignores. As an independent gate it covers the case the supervised model structurally cannot — a pattern absent from training data — and it can only ever escalate, never approve. |
| **Paired bootstrap for the ablation** | The two models are scored on the same orders, so their errors are correlated; an unpaired interval would overstate the uncertainty on the *difference* and might have let me claim a win I do not have. |
| **Chronological split, not K-fold** | The problem is temporal and production scores forward in time. K-fold would let the model learn from the future, which is the whole class of leakage I am trying to avoid. |
| **Rules before the LLM** | The deterministic rules are the highest-precision signals (non-serviceable pincode, blocklist, ring velocity) and they must not be negotiable. Running them first means the LLM never sees a case where it could talk itself past a hard constraint. |
| **Agent only on AMBER** | Green and red are already decided; spending a model call on them buys nothing and costs latency and quota. Amber is where the marginal information actually changes the action. |
| **Closed action set + schema-constrained output** | The LLM picks *among* actions rather than describing one, so an invalid action is a parse failure rather than a bad decision. Anything it returns outside the set falls back to the deterministic core. |
| **Target encoding with a train-only prior** | The shrinkage means a pincode seen twice is mostly prior, not memorised outcome, which is what stops rare-category leakage. The prior comes from train only so validation and test cannot leak backwards through it. |
| **7-day outcome lag** | An order placed today cannot know if yesterday's was returned — the courier has not attempted delivery. Without the lag I would be training on knowledge the live scorer never has. |
| **Cost per 1,000 orders, not total** | Totals scale with the test split size and are not comparable across datasets or merchants. Per-1k is the unit a merchant can multiply by their own volume. |

## Cutting order if you run long

1. Fraud Rings tab (mention in one line instead).
2. The batch-mode tab (the audit trail already carries the bounded-agent story).
3. The copilot chat.

**Never cut:** the opening cost table, the Evidence tab, or the leakage toggle. Those three are the submission.
