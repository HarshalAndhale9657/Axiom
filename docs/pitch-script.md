# The 5-minute pitch — word-for-word script

The companion to [pitch.md](pitch.md), which holds the beat sheet, the judge Q&A and the
design-decision defences. **This file is the thing you read while recording.**

Every word of narration is here, with the screen action beside it. The timings are computed
from the actual word counts, not estimated — regenerate them any time with:

```bash
python docs/scripts/script_timing.py
```

**738 words.** At **150 words per minute** — a brisk but natural technical delivery — that
is **4:55**. At a slower 140 it is 5:16, which is over. So rehearse against a timer, and if
you land past five minutes use the [cut list](#if-you-are-running-long) rather than speeding
up: rushed numbers are worse than fewer numbers. The cut list frees about 41 seconds.

**The one idea a judge should retain:**
> *Razorpay already grades COD risk. Axiom is the evidence layer that proves — in rupees,
> out-of-sample, with the break-even published — which grade is right and what being wrong costs.*

---

## Before you hit record

- [ ] `uvicorn src.api.main:app` running, and **warmed** — load `/metrics`, `/baselines`, `/slices` once. The ablation trains two models on first call; do not put that latency on camera.
- [ ] `npm --prefix web run dev` running. Dashboard on **Risk Queue**, **light theme**, ~1440px, zoom 90%.
- [ ] Run one batch and log one override **before** recording, so the Audit tab is populated when you reach beat ④.
- [ ] `.env` has `GEMINI_API_KEY` and `OPENAI_API_KEY`. **Check the quota is not exhausted.** If it is, the deterministic fallback will show — say so on camera rather than hide it. Here that is a feature, not an excuse.
- [ ] Terminal open at the repo root, font size up, ready for `pytest -q`.
- [ ] Notifications off. Bookmarks bar hidden. One take if you can manage it.
- [ ] Water. You are talking for five minutes without a pause.

**Say the numbers like a person.** Round when speaking, exact on screen:

| On screen | Say |
|---|---|
| ₹71,776 | "seventy-two thousand rupees" |
| ₹64,795 | "sixty-five thousand" |
| ₹1,570 | "fifteen hundred rupees" |
| ₹123 / ₹138 | "one-twenty-three" / "one-thirty-eight" |
| 0.97 / 0.80 | "nought point nine seven" / "nought point eight" |
| −0.038 | "minus nought point nought three eight" |
| 0.0027 PR-AUC | "three thousandths of PR-AUC" |
| 3.8× | "three point eight times" |

---

# THE SCRIPT

---

## ① The problem · ~19s
**Screen:** Risk Queue, full console. Don't move the mouse — let them see a working product while you talk.

> Cash on delivery is sixty percent of Indian e-commerce, and about a quarter of those orders come straight back. Return to origin — the merchant pays the courier both ways and sells nothing.
>
> The obvious fix is to stop taking COD from risky customers. I measured what that costs.

**Delivery:** Flat and factual. No enthusiasm yet. The last line is a setup — land it and move.

---

## ② The counterintuitive number, and immediately its break-even · ~30s
**Screen:** Economics tab → the three-row cost table. Cursor resting on the "Block all COD" row.

> Blocking every COD order costs seventy-two thousand rupees per thousand orders. Doing nothing costs sixty-five. **The blunt control is worse than no control** — friction on good customers is not free.
>
> That is a claim, not a measurement. So it ships with its break-even: it holds while challenging a genuine customer costs more than one-twenty-three rupees. I assume one-thirty-eight. Twelve percent headroom. Thin — and I'd rather show the pivot than hide it.

**Delivery:** Pause a full beat after "worse than no control." That sentence buys you the next four minutes. Then take the break-even briskly — you are volunteering a weakness and it should sound routine, not apologetic.

---

## ③ The product, on one real case · ~48s
**Screen:** Risk Queue → click an **amber** order → SHAP bars → **Investigate** → verifier verdict → **Execute on Razorpay**.

> Every order gets a calibrated probability of return — a probability, not a score, because everything downstream is rupee arithmetic on it.
>
> Why this one is flagged: incomplete address, tier-three pincode, COD, first-time buyer. SHAP attributions — real per-order factors, not a template.
>
> Only amber reaches the agent. It runs typed tools, retrieves the matching policy clause, and returns a schema-constrained decision from six allowed actions. It cannot invent a seventh or change the score.
>
> A second model, from a different vendor, can veto it — and a veto escalates to a human.
>
> And the action is real: a genuine Razorpay test-mode link. No money moves, but the rail is real.
>
> Convert to prepaid. Not a ban. Every action here is reversible.

**Delivery:** The only stretch where you demo rather than argue, so let the clicks breathe. Click **Investigate** *as* you say "Only amber reaches the agent" — the trace fills while you describe it, which beats clicking into dead air. Slow down on the last line; it's the ethical core.

---

## ④ Bounded, audited, overridable · ~15s
**Screen:** Override the agent's decision → Audit Trail tab.

> I disagree with the agent, so I override it — logged, before and after, with my name on it.
>
> This table is append-only, enforced by database triggers. `UPDATE` and `DELETE` are blocked at the storage layer, not by convention.

**Delivery:** "not by convention" is the phrase that lands — a payments engineer hears the difference immediately.

---

## ⑤ Scale, and failure · ~20s
**Screen:** Batch tab, the completed run with its stop reason visible.

> It also works the queue unattended. Thirty orders, twelve returns caught, eighteen good customers frictioned — and it stopped itself on its call budget. That is the guardrail firing, not a crash.
>
> When the model is down it falls back to the deterministic core, and the trace says so.

**Delivery:** Say "eighteen good customers frictioned" clearly and without softening it. Volunteering the unflattering half of the ratio is the whole point — a judge who has watched fifty videos has not heard anyone do that.

---

## ⑥ The part that is actually being graded · ~1:47
**Screen:** Evidence tab. Scroll slowly, one exhibit per point. **This section wins or loses the submission — do not rush it.**

> Track two says: honest metrics, including false-positive cost. So here is where I tried hardest to prove myself wrong.
>
> **One — the threshold was chosen without looking at the test set.** Everyone sweeps a cost curve and quotes its minimum. But on test data that minimum is an oracle you can never reach in production. Mine is fitted on validation and frozen before the test split is scored. Tuning on test would have looked fifteen hundred rupees per thousand better. That number is on screen because I did not take it.
>
> **Two — I found a leak inside my own leakage-safe pipeline.** I already split by time. But an order placed today cannot know whether yesterday's was returned — the courier has not attempted delivery yet. So label-derived history now waits seven days. It cost three thousandths of PR-AUC. Published, not buried.
>
> **Three — I report the comparison I lose.** Against a plain logistic regression, the paired interval spans zero. I have not shown my model is better, and that is on the page. The reason is my own generator: it builds risk as a purely additive weighted sum, so logistic regression is correctly specified and cannot be beaten here.
>
> **Four — I name the good customers who pay for my false positives.** A genuine tier-three buyer is three point eight times more likely to be challenged than a tier-one buyer. That is why the response is *verify*, never *block*.
>
> Every number has a confidence interval, and none is typed by hand.

**Screen:** cut to terminal → `python -m src.model.full_report --check`

> One command regenerates all of it — and a test fails the build if my README disagrees.

**Delivery:** Four numbered claims, and the numbering does real work — a judge can follow four things, not a paragraph. Pause between each. On point three, *"I have not shown my model is better"* is the most counter-intuitive sentence in the video: say it without flinching, then explain. Let the terminal command actually finish on screen; it's proof, not decoration.

---

## ⑦ The impressive lie · ~26s
**Screen:** Economics tab → the leaky / honest toggle, side by side.

> Public RTO models advertise ninety-nine percent AUC. Here is that number on my own data, in one line of code: nought point nine seven — by fitting the encoders on every row including its own label.
>
> It is worthless. The model memorised the answer. My real number is nought point eight.
>
> I built the lie so I could show you why I did not ship it.

**Delivery:** The last line is your closing hook — deliver it to the camera, not the screen. Then stop. Add nothing.

---

## ⑧ Close · ~28s
**Screen:** terminal, `pytest -q` finishing on **178 passed**.

> A hundred and seventy-eight tests, including the leakage guards and the claim checks on the README. CI rebuilds the data and the model from scratch on every push.
>
> My pitch is not that I built the most accurate model. It is that **every number I have shown you is one I could defend in a review** — and on a system that touches money, that is the only kind worth having.

**Delivery:** Let `pytest` land on the count before you start the second paragraph. Then hold two seconds of silence before you stop recording — it reads as confidence, and it gives an editor a clean out.

---

## If you are running long

Cut in this order. Each is written so the video still stands without it.

| # | Cut | Saves | Why it's safe |
|---|---|---|---|
| 1 | ⑥'s closing line, "One command regenerates all of it…" | ~7s | The `--check` command running on screen already makes the point |
| 2 | ⑤'s second sentence, "When the model is down…" | ~7s | The audit trail already implies bounded behaviour |
| 3 | ③'s "Why this one is flagged…" list | ~8s | The SHAP bars are on screen; let them speak for themselves |
| 4 | ⑦'s "It is worthless. The model memorised the answer." | ~3s | "I built the lie so I could show you why I did not ship it" carries it alone |
| 5 | ④ entirely, mentioning the audit trail in one line during ⑥ | ~16s | Last resort — this costs you the bounded-AI evidence |

Taking 1 through 4 lands you at **4:30** and keeps every graded claim intact.

**Never cut:** the cost table in ②, any of the four numbered claims in ⑥, or the leakage
toggle in ⑦. Those three are the submission.

## If something breaks on camera

Do not stop recording. Each of these is a better moment than a clean take.

| If | Say |
|---|---|
| Gemini is rate-limited and the trace says `fallback` | "That's the free-tier quota — and this is the fallback I mentioned. The deterministic core decided it, the trace says so, and the recommendation is still bounded and audited. It degrades honestly." |
| The verifier is slow or errors | "The verifier is a second vendor, so it's a second network call. When it fails, the case escalates to a human rather than auto-executing." |
| The Razorpay link fails | "Test-mode API — and the actuator's failure path is the agent's: nothing executes, the case escalates, and the attempt is in the audit log." |
| You fumble a number | State the correct one and carry on. Don't apologise. Your whole thesis is that the numbers are checkable. |
| You lose your place | Go to the Evidence tab and start the next numbered claim. The four are independent by design. |

---

## The last thing to remember

You are not competing on model accuracy. You have a null result against logistic regression
and you say so out loud. You are competing on being **the one submission whose numbers a
reviewer could not knock down.** Every beat above exists to demonstrate that, and the video
has done its job the moment a judge thinks: *this person would be safe near production.*
