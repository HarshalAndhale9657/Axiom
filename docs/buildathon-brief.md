# Razorpay AI Buildathon — Complete Info & Track Analysis

> **Tagline:** *"Build. Show. Get hired."* · *"Think you can build real AI? Prove it."*
> **Core idea:** Your code speaks louder than your resume.
> **Official site:** https://razorpay.com/buildathon/
> **Compiled:** 2026-08-23

---

## 1. TL;DR — The Essentials

| Item | Detail |
|---|---|
| **What it is** | A student-only buildathon to recruit **AI Builder Interns** at Razorpay |
| **Stipend** | **₹75,000 / month** |
| **Duration** | **6 or 12 months** (your choice) |
| **Mode / Location** | **In-person, Bangalore** |
| **Starts** | **September** |
| **Eligibility** | **Students only** (currently enrolled). Reported grad years: **2027 / 2028 / 2029**, any degree stream* |
| **Application deadline** | **5 September 2026** (reported via announcements — *confirm on the form*) |
| **How to apply** | Google Form: `forms.gle/d9r2gvxp8cmoZhon9` (linked from the site) |
| **Selection** | Build → submit → panel interview. **No resume screening, no aptitude test, no group discussion** |

\* *Grad-year/degree specifics come from third-party job aggregators, not the official page. Verify on the application form before relying on them.*

---

## 2. The Application Process (4 Steps)

The whole point of the event is to **replace conventional screening with real project work**:

> *"No resume screening. No long application. Four steps: pick a track, build something real, show your work (a public repo, a 5 minute pitch video, the architecture), and if it has signal we call you in."*

1. **Pick a track** (one of the 5 below).
2. **Build something real** — a working, functional product (not a concept/mockup).
3. **Show your work**, which means submitting:
   - a **public code repository** (GitHub),
   - a **5-minute pitch video**,
   - the **architecture** (your design + decisions).
4. **If it has "signal," they call you in.**

**After submission:**
> *"Shortlisted builders go straight to a panel. No aptitude test. No group discussion."*

So the pipeline is: **Apply + submit project → shortlist based on "signal" → panel interview** (where you walk through architecture and defend your choices).

### What a strong submission looks like
- Working, functional code — **not conceptual**.
- Public GitHub repo with **clear documentation, a professional README, and a real commit history**.
- A tight **5-minute pitch** showing you understand the problem → solution.
- Ability to **defend your architectural decisions** in the panel.

---

## 3. The Five Tracks — Full Analysis

Each track below has: the **brief**, the **evaluation bar** (the exact standard Razorpay stated), what it's **really testing**, concrete **project ideas**, and the **traps to avoid**.

A pattern runs through all of them: **Razorpay isn't impressed by demos — they want bounded, auditable, measured AI acting on money.** Every track rewards honesty (real metrics, handled failures, audit trails) and punishes cherry-picking. Build accordingly.

---

### Track 1 — AI Growth & Agentic Commerce

**Brief:** Build agents that increase merchant revenue or enable AI-buyer transactions using **Razorpay test APIs**.

**Evaluation bar (verbatim):**
> *"Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully."*

**What it's really testing:** Can you let an AI agent *take real money actions* (create payment links, apply discounts, upsell, checkout as an AI buyer) **safely**? The word that matters is **gated** — a human or rule must approve/limit each money-moving step.

**Project ideas:**
- An agent that watches merchant data and **auto-generates targeted offers / payment links** to recover or grow revenue.
- An **"AI buyer" agent** that completes a purchase flow via Razorpay test APIs (add to cart → checkout → pay), with spend caps.
- A merchant-side **upsell/cross-sell agent** at checkout that is bounded by margin rules.

**Must-haves to clear the bar:**
- Every money action is **explainable** (log *why* it happened), **bounded** (spend/frequency caps), and **gated** (approval or hard rule before execution).
- A visible **audit trail** of all actions.
- **Demonstrate one failure handled gracefully** (e.g., API declines / a bad recommendation → agent stops safely, rolls back, alerts).

**Traps:** An unconstrained agent that "just spends" or auto-discounts with no guardrails. No audit log. Only showing the happy path.

---

### Track 2 — AI Risk Manager

**Brief:** Develop **detectors, verifiers, or auto-responders** for **fraud, returns, or chargebacks**, with **measured precision/recall**.

**Evaluation bar (verbatim):**
> *"Honest metrics including false-positive cost. Strictly defense-only: anything offense-capable is disqualified."*

**What it's really testing:** Real ML/AI evaluation discipline. Anyone can flag transactions; can you flag them **accurately** and **honestly report the cost of being wrong**?

**Project ideas:**
- A **fraud/chargeback detector** with a labeled (or synthetic) dataset and a full precision/recall/F1 breakdown.
- A **returns-abuse verifier** that scores return requests for likely abuse.
- An **auto-responder** that takes a *defensive* action (hold, request verification, escalate) when risk crosses a threshold.

**Must-haves to clear the bar:**
- **Report precision AND recall**, plus the **false-positive cost** (what happens to good customers you wrongly flag).
- Be transparent about failure modes — **no cherry-picked numbers**.
- **Defense-only.** ⚠️ Anything that could be used to *commit* fraud/evade detection is an **automatic disqualification**.

**Traps:** Reporting only accuracy (useless on imbalanced fraud data). Hiding false positives. Building anything "offense-capable."

---

### Track 3 — AI Revenue Recovery

**Brief:** Create agents that **identify revenue risks** and **execute bounded recovery workflows** across **payment failures, abandonments, and receivables**.

**Evaluation bar (verbatim):**
> *"Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."*

**What it's really testing:** End-to-end **agentic workflow execution with measurable ₹ outcome** — not a single lucky recovery, but performance **across a batch**.

**Project ideas:**
- A **failed-payment retry agent**: smart retry timing, alternate payment methods, dunning messages — measure recovery rate over a batch.
- A **cart-abandonment recovery agent**: detect abandonment → bounded nudge sequence → measure conversions.
- A **receivables/collections agent**: prioritize overdue invoices, send compliant reminders, escalate on rules.

**Must-haves to clear the bar:**
- **Measured money recovered across a batch** (e.g., "recovered ₹X across N cases, Y% recovery rate").
- **Compliant escalation** (respect communication rules/limits).
- **Stopping rules** (know when to give up / stop contacting — don't spam).
- A full **audit trail**.

**Traps:** Showing one recovered payment. No stopping rules (agent that harasses). No compliance consideration. No ₹ number.

---

### Track 4 — AI Finance Controller

**Brief:** Build agents that **close finance-ops loops** across **50+ synthetic records**, with **match-rate reporting** and **exception identification**.

**Evaluation bar (verbatim):**
> *"Throughput plus measured accuracy plus an honest exception list. One cherry-picked match proves nothing."*

**What it's really testing:** **Reconciliation at scale** with honest accounting for what *didn't* match. This is the most "back-office finance automation" track.

**Project ideas:**
- A **reconciliation agent**: match payments ↔ invoices ↔ settlements across 50+ synthetic records, report match rate, flag exceptions.
- An **expense/ledger auto-categorizer** that closes the books and surfaces anomalies.
- An **invoice ↔ bank-statement matcher** that lists every unmatched item with a reason.

**Must-haves to clear the bar:**
- Process **50+ synthetic records** (build a realistic synthetic dataset).
- Report **throughput** (records/time) **and measured accuracy** (match rate).
- Produce an **honest exception list** — every record it couldn't confidently match, and why.

**Traps:** Demoing on 3 perfect records. Hiding mismatches. No exception list. "One cherry-picked match proves nothing" — they said it literally.

---

### Track 5 — Open Track

**Brief:** Submit solutions addressing problems **outside the predefined categories**, using **meaningful AI implementation**.

**Evaluation bar (verbatim):** You must demonstrate
> *"a real problem, a working product, meaningful use of AI, and evidence that it creates value."*

**What it's really testing:** Whether you can independently find a real problem and ship a genuinely useful, AI-powered product — with **evidence of value**, not novelty for its own sake.

**Must-haves to clear the bar:**
- **A real problem** (clearly articulated, someone actually has it).
- **A working product** (functional, not a mockup).
- **Meaningful use of AI** (AI is core, not a bolt-on gimmick).
- **Evidence it creates value** (metrics, user feedback, before/after).

**Traps:** A cool AI demo that solves no real problem. AI used as a buzzword. No evidence of value.

---

## 4. Cross-Track Patterns — What Razorpay Actually Rewards

Reading all five bars together, the same values repeat. **Bake these into whatever you build:**

1. **Bounded & gated** — the AI acts within hard limits; money actions need approval/rules.
2. **Auditable** — there is a log/trail of every decision and action.
3. **Measured & honest** — real metrics, including the *cost of being wrong* (false positives, exceptions, failures). **No cherry-picking.**
4. **Graceful failure** — you deliberately show a failure being handled well.
5. **Scale over anecdote** — batches and 50+ records beat single lucky demos.
6. **Defense-only / safe** — especially Track 2, anything offensive = disqualified.

These are exactly the traits a fintech needs in engineers who touch money. **Signal = a build that a payments company could actually trust near real transactions.**

---

## 5. Recommended Track Choice (quick guidance)

- **Strongest at ML/data science, evaluation, metrics** → **Track 2 (AI Risk Manager)**.
- **Strong at agents / workflow orchestration + APIs** → **Track 1 (Agentic Commerce)** or **Track 3 (Revenue Recovery)**.
- **Like clean back-office automation + data plumbing** → **Track 4 (Finance Controller)** — arguably the *easiest to score well* because success is objective (match rate + exceptions).
- **Have a killer original idea already** → **Track 5 (Open)** — but the bar for "evidence of value" is high.

**Pragmatic pick:** Track 3 or Track 4 tend to give the clearest, most measurable ₹/accuracy story, which maps directly onto the evaluation bars.

---

## 6. Suggested Build Plan (applies to any track)

1. **Generate/obtain a realistic synthetic dataset** (records, transactions, invoices — whatever the track needs). Realism matters.
2. **Build the core agent/model** using the **latest Claude models** and Razorpay **test** APIs where relevant.
3. **Add the guardrails first-class:** bounds, gates, stopping rules, audit logging — these *are* the grade, not extras.
4. **Instrument metrics** from day one (precision/recall, recovery ₹, match rate, throughput).
5. **Deliberately build one failure scenario** and handle it gracefully on camera.
6. **Write a professional README** (problem → approach → architecture → results → how to run) and keep a **clean commit history**.
7. **Record the 5-min pitch:** problem, live demo, architecture, honest metrics, the handled failure. Tight and rehearsed.
8. **Prep for the panel:** be able to defend every architectural decision and trade-off.

---

## 7. Open Questions to Verify on the Official Form

- Exact **application deadline** (announced as **5 Sep 2026**, but confirm on the form).
- Whether it is **individual or team** (team size not officially stated).
- **Grad-year / degree** eligibility specifics (2027–2029 & "any stream" are from aggregators, not official).
- Whether the **project is submitted with the application** or after shortlisting.
- Exact **program start date** in September and round dates ("announced to shortlisted applicants").

---

## 8. Sources

- Official: [Razorpay AI Buildathon](https://razorpay.com/buildathon/)
- [Velonx — Buildathon 2026: Tracks, Eligibility, Stipend & Selection](https://velonx.in/blog/razorpay-ai-buildathon-2026-tracks-eligibility-stipend-selection-process)
- [OffCampusJobs4u — Razorpay AI Intern ₹75,000 Stipend](https://offcampusjobs4u.com/razorpay-internship-2026-ai-intern/)
- [Placement-Officer — Razorpay AI Buildathon 2026](https://www.placement-officer.com/2026/08/razorpay-ai-buildathon-2026-build-ai.html)
- [CourseJoiner — Razorpay AI Builder Internship 2026](https://coursejoiner.com/internship/razorpay-ai-builder-internship-2026/)
- Announcement noting deadline: [X/Twitter post](https://x.com/ajay_2512x/status/2090393869473165453)
