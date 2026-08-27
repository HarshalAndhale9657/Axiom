"""Autonomous batch mode for Axiom — work the whole AMBER queue with real stopping rules.

The agent processes borderline (amber) orders unattended and reports the batch economics.
Honesty is the point:

* Rupees are measured **post-hoc against the labelled held-out TEST batch** (we know each
  order's true ``is_rto``), never on training data.
* We report the **full 2x2**, not a cherry-picked number: gross ₹ recovered (prevented-RTO
  cost on flagged orders that *would* have returned), the **friction cost we incurred on
  genuine customers** (the honest downside), and the resulting **net**.
* The one modelling assumption — that an applied friction (verify / prepaid / part-pay)
  prevents that return — is stated, not hidden.
* Stopping rules are genuine (max orders, LLM-call budget, consecutive-low-value cutoff,
  quiet hours), so the batch never spams (mirrors policy ``RTO-POL-5`` contact limits).

This module holds only pure, unit-testable logic; :class:`RiskEngine` supplies the data.
"""
from __future__ import annotations

from dataclasses import dataclass

# Any action other than a clean approve is an "intervention" (friction / review / re-rail).
INTERVENTION_ACTIONS = {
    "step_up_verification", "part_pay_cod", "convert_cod_to_prepaid",
    "escalate_to_human", "hold_for_review",
}


@dataclass
class BatchConfig:
    """Stopping rules for an autonomous run — all real, all defensible."""
    max_orders: int = 30              # hard cap on orders processed per run
    budget_calls: int = 30            # cap on LLM investigate() calls (cost guard)
    stop_after_low_value: int = 10    # stop after K consecutive low-value orders (diminishing returns)
    low_value_threshold: float = 400.0
    quiet_hours: tuple[int, int] | None = None  # (start, end) local hour; skip run if now inside


@dataclass
class BatchState:
    processed: int = 0
    calls: int = 0
    consecutive_low_value: int = 0


def is_intervention(action: str) -> bool:
    """True if the action adds friction / review rather than cleanly approving."""
    return action in INTERVENTION_ACTIONS


def in_quiet_hours(now_hour: int | None, quiet: tuple[int, int] | None) -> bool:
    """True if ``now_hour`` falls in the quiet window; supports an overnight wrap like (22, 6)."""
    if quiet is None or now_hour is None:
        return False
    start, end = quiet
    if start == end:
        return False
    if start < end:
        return start <= now_hour < end
    return now_hour >= start or now_hour < end   # window wraps past midnight


def recovered_and_cost(action: str, is_rto: int, c_fn_value: float,
                       c_fp_value: float) -> tuple[float, float]:
    """(recovered, friction_cost) for one processed order under the stated assumption.

    * intervention on an order that WOULD have returned  -> we recover its ``c_fn``.
    * intervention on a genuine customer                 -> we incur friction cost ``c_fp``.
    * a clean approve                                    -> no rupee effect here (a missed RTO
      is accounted separately by the caller as un-recovered cost).
    """
    if not is_intervention(action):
        return 0.0, 0.0
    if is_rto:
        return float(c_fn_value), 0.0
    return 0.0, float(c_fp_value)


def stop_reason(state: BatchState, config: BatchConfig) -> str | None:
    """Return a human-readable stop reason if any rule has fired, else None."""
    if state.processed >= config.max_orders:
        return f"reached max orders ({config.max_orders})"
    if state.calls >= config.budget_calls:
        return f"reached LLM call budget ({config.budget_calls})"
    if state.consecutive_low_value >= config.stop_after_low_value:
        return (f"stopped after {config.stop_after_low_value} consecutive "
                f"low-value orders (< ₹{config.low_value_threshold:.0f})")
    return None


def update_state(state: BatchState, order_value: float, config: BatchConfig) -> None:
    """Advance counters after one processed order (mutates ``state``)."""
    state.processed += 1
    state.calls += 1
    if order_value < config.low_value_threshold:
        state.consecutive_low_value += 1
    else:
        state.consecutive_low_value = 0
