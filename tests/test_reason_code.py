"""Tests for grounded LLM reason codes (offline via MockProvider).

The point of these tests: the prompt is *grounded* (only provided facts appear), the system
instruction forbids invention, and the system degrades gracefully to the deterministic SHAP
reason when the LLM fails.
"""
from __future__ import annotations

import pytest

from src.agent.llm import LLMError, MockProvider
from src.agent.reason_code import SYSTEM, build_prompt, generate_reason_code
from src.model.explain import Explanation, Factor


@pytest.fixture()
def explanation() -> Explanation:
    return Explanation([
        Factor("address_completeness", "address quality", 0.2, 0.9, "raises"),
        Factor("is_cod", "COD payment", 1.0, 0.6, "raises"),
        Factor("account_age_days", "account age", 800.0, -0.1, "lowers"),
    ])


def test_prompt_is_grounded_in_provided_facts(explanation):
    prompt = build_prompt("O1", 0.62, "amber", "step_up_verification",
                          explanation.as_payload(), ["RTO-POL-3.2 amber step-up"])
    assert "O1" in prompt and "step_up_verification" in prompt
    assert "address quality" in prompt and "COD payment" in prompt
    assert "RTO-POL-3.2" in prompt
    # nothing fabricated: a feature not in the factors must not appear
    assert "device" not in prompt.lower()


def test_system_prompt_forbids_invention():
    assert "do not invent" in SYSTEM.lower()


def test_generate_uses_provider_and_returns_text(explanation):
    mock = MockProvider(canned="Elevated risk: poor address quality on a COD order.")
    out = generate_reason_code(explanation, order_id="O1", risk_score=0.62, band="amber",
                               action="step_up_verification", provider=mock)
    assert out == "Elevated risk: poor address quality on a COD order."
    # the grounded system instruction was actually passed to the model
    assert mock.calls and "do not invent" in mock.calls[0]["system"].lower()


def test_falls_back_to_deterministic_reason_on_llm_error(explanation):
    class Boom:
        def generate(self, *a, **k):
            raise LLMError("down")

    out = generate_reason_code(explanation, order_id="O1", risk_score=0.62, band="amber",
                               action="step_up_verification", provider=Boom())
    assert out == explanation.grounded_reason()
    assert "address quality" in out
