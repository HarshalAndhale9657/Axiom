"""Tests for the provider-agnostic LLM layer — the Gemini->OpenAI fail-over chain."""
from __future__ import annotations

import pytest

from src.agent.llm import FallbackProvider, LLMError, MockProvider, provider_vendor


class _Boom:
    """A provider that always fails (simulates a 429/quota-exhausted vendor)."""
    def generate(self, prompt, **kw):
        raise LLMError("boom")


def test_fallback_falls_through_to_next_on_error():
    fp = FallbackProvider([("google", _Boom()), ("openai", MockProvider(canned="OK"))])
    assert fp.generate("x") == "OK"
    assert fp.last_vendor == "openai"          # records the vendor that actually served


def test_fallback_prefers_the_first_working_provider():
    fp = FallbackProvider([("google", MockProvider(canned="G")), ("openai", MockProvider(canned="O"))])
    assert fp.generate("x") == "G" and fp.last_vendor == "google"


def test_fallback_raises_when_all_providers_fail():
    fp = FallbackProvider([("google", _Boom()), ("openai", _Boom())])
    with pytest.raises(LLMError):
        fp.generate("x")


def test_fallback_requires_at_least_one_provider():
    with pytest.raises(LLMError):
        FallbackProvider([])


def test_provider_vendor_reports_chain_and_mock():
    assert provider_vendor(MockProvider()) == "mock"
    fp = FallbackProvider([("openai", MockProvider(canned="O"))])
    fp.generate("x")
    assert provider_vendor(fp) == "openai"
