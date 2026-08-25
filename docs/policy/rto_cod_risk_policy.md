# Axiom RTO/COD Risk Policy (v1)

> This document is **both** (a) the human-readable governance for risk decisions and (b) the knowledge base the Claude agent retrieves over (RAG). Every automated action must cite a rule ID from this document. **Defense-only:** every rule protects the platform and honest customers; none assists fraud.

---

## RTO-POL-1 — Risk bands
Risk score `s ∈ [0,1]` from the calibrated model maps to bands by **cost-optimal thresholds** (`τ_low`, `τ_high`) chosen from the cost-vs-threshold analysis, not by gut:
- **GREEN** (`s < τ_low`) — low risk. Proceed frictionless.
- **AMBER** (`τ_low ≤ s < τ_high`) — borderline. Investigate + step-up. (This is the only band the agent investigates — mirrors "Grey" review.)
- **RED** (`s ≥ τ_high`) — high risk. Protective action + human escalation.

Bands are advisory to the **deterministic rules**, which run first and can override (below).

---

## RTO-POL-2 — Deterministic rules (run BEFORE the model/LLM; highest precision)
- **RTO-POL-2.1 Auto-approve:** verified repeat buyer with ≥3 prior delivered orders and prior-RTO-rate < 5% **and** prepaid → GREEN regardless of score.
- **RTO-POL-2.2 Non-serviceable:** if delivery pincode is non-serviceable/undeliverable → RED, action = `hold_for_review` (never silently fail).
- **RTO-POL-2.3 Blocklist:** device/phone on the confirmed-abuse blocklist → RED, `hold_for_review` + escalate.
- **RTO-POL-2.4 Velocity ring:** > N orders from the same device/phone within a short window (fraud-ring signal) → RED, escalate.
- Rules are transparent and logged; no rule blocks a customer without a stated reason.

---

## RTO-POL-3 — Tiered response (bounded action space)
Allowed actions (nothing else is possible): `approve` · `step_up_verification` · `part_pay_cod` · `convert_cod_to_prepaid` · `hold_for_review` · `escalate_to_human`.
- **RTO-POL-3.0 Part-pay (dynamic friction):** for amber COD orders, require a small upfront deposit (5–10% of order value via UPI) — "skin in the game" that deters casual cancellation/impulse orders while keeping COD alive. Preferred over outright block; a legitimate buyer simply pays a nominal deposit.
- **RTO-POL-3.1 Green:** `approve`, frictionless.
- **RTO-POL-3.2 Amber:** `step_up_verification` — send COD-confirmation OTP or address-confirmation; **and/or** offer a prepaid link. Risk is re-scored after verification and may downgrade to GREEN.
- **RTO-POL-3.3 Red:** `hold_for_review` and/or `convert_cod_to_prepaid`; `escalate_to_human` if the buyer is high-value or the case is ambiguous.

---

## RTO-POL-4 — COD → prepaid conversion
- **RTO-POL-4.1** For amber/red COD orders, offer a one-click prepaid payment link, optionally with a small incentive (e.g., ₹50 off). This *protects* the merchant while giving the buyer a frictionless path — it does not cancel the order outright.
- **RTO-POL-4.2** Prefer conversion/step-up over outright block wherever possible — **the cost of blocking a good customer is high** (false-positive cost is a first-class metric).

---

## RTO-POL-5 — Stopping rules & communication limits (bounded, humane)
- **RTO-POL-5.1** Maximum **2** verification nudges per order over a **48-hour** window; then auto-cancel or route to human — never spam.
- **RTO-POL-5.2** Respect quiet hours (no messages 21:00–08:00 local).
- **RTO-POL-5.3** Every outbound action is rate-limited and logged.

---

## RTO-POL-6 — Human-in-the-loop & escalation
- **RTO-POL-6.1** Any RED decision on a high-value order, and any case where agent confidence < 0.6, must be escalated to a human reviewer.
- **RTO-POL-6.2** A human can override any automated decision. The override (reviewer id, timestamp, reason, before/after) is written to the audit trail.
- **RTO-POL-6.3** The model/agent recommends; on escalated cases the human decides.

---

## RTO-POL-7 — Explainability & audit
- **RTO-POL-7.1** Every decision records: input, model version, score, top SHAP factors, agent tool calls, action, confidence, policy citations, and (if any) human override.
- **RTO-POL-7.2** Reason codes are **grounded**: the explanation may reference *only* the provided SHAP factors and retrieved policy — no invented justifications.
- **RTO-POL-7.3** The audit log is append-only (immutable).

---

## RTO-POL-8 — Fairness & defense-only posture
- **RTO-POL-8.1** Do not use protected attributes as risk features. Pincode risk is a serviceability/logistics signal, monitored for disparate impact.
- **RTO-POL-8.2** Axiom only scores, flags, verifies, and applies protective actions. It contains nothing that helps commit or evade fraud. Anything offense-capable is out of scope by policy.
