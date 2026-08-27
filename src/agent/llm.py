"""Provider-agnostic LLM interface for Axiom.

Design: a tiny stable ``LLMProvider`` protocol so the reason-code + agent layers never
bind to a vendor. Default is **Gemini** on the free tier, spoken over plain REST (no heavy
SDK, no version churn). A ``MockProvider`` makes the whole stack testable offline with no
network or key. Swapping to Groq / OpenAI / local Ollama is a one-class change.

Pitch framing: *architected for the Claude Agent SDK (Razorpay's own stack), demonstrated
on a free tier to prove it's vendor-portable and runs at zero marginal cost.*
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol, runtime_checkable

from src.util import load_env


class LLMError(RuntimeError):
    """Raised on any provider/transport failure (callers fall back gracefully)."""


@runtime_checkable
class LLMProvider(Protocol):
    def generate(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.0, max_output_tokens: int = 256,
                 thinking_budget: int | None = 0, response_schema: dict | None = None) -> str:
        ...


class GeminiProvider:
    """Google Gemini via the Generative Language REST API (free tier)."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        load_env()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model or os.environ.get("AXIOM_GEMINI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise LLMError("GEMINI_API_KEY is not set (put it in .env)")

    def generate(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.0, max_output_tokens: int = 256,
                 thinking_budget: int | None = 0, response_schema: dict | None = None) -> str:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self.api_key}")
        gen_cfg: dict = {"temperature": temperature, "maxOutputTokens": max_output_tokens}
        # Gemini 2.5+ spends "thinking" tokens from the output budget by default, which can
        # starve short answers. We disable it (budget 0) for concise grounded outputs.
        if thinking_budget is not None:
            gen_cfg["thinkingConfig"] = {"thinkingBudget": thinking_budget}
        # Force valid JSON matching a schema (used by the agent's structured decision).
        if response_schema is not None:
            gen_cfg["responseMimeType"] = "application/json"
            gen_cfg["responseSchema"] = response_schema
        payload: dict = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen_cfg}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        def _post(pl: dict) -> dict:
            req = urllib.request.Request(url, data=json.dumps(pl).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())

        try:
            data = _post(payload)
        except urllib.error.HTTPError as exc:
            # A model that rejects thinkingConfig -> retry once without it.
            if "thinkingConfig" in gen_cfg:
                gen_cfg.pop("thinkingConfig")
                try:
                    data = _post(payload)
                except urllib.error.HTTPError as exc2:
                    raise LLMError(f"Gemini HTTP {exc2.code}: {exc2.read().decode()[:200]}") from exc2
            else:
                raise LLMError(f"Gemini HTTP {exc.code}: {exc.read().decode()[:200]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise LLMError(f"Gemini transport error: {exc}") from exc

        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Gemini returned an unexpected shape: {str(data)[:200]}") from exc


class MockProvider:
    """Deterministic offline provider for tests/CI. Echoes the last prompt line by default."""

    def __init__(self, canned: str | None = None) -> None:
        self.canned = canned
        self.calls: list[dict] = []

    def generate(self, prompt: str, *, system: str | None = None,
                 temperature: float = 0.0, max_output_tokens: int = 256,
                 thinking_budget: int | None = 0, response_schema: dict | None = None) -> str:
        self.calls.append({"prompt": prompt, "system": system, "schema": response_schema})
        if self.canned is not None:
            return self.canned
        return "MOCK: " + prompt.strip().splitlines()[-1][:80]


class OpenAIProvider:
    """OpenAI chat models (e.g. gpt-4o-mini) — used as the INDEPENDENT cross-vendor verifier."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        load_env()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or os.environ.get("AXIOM_OPENAI_MODEL", "gpt-4o-mini")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set (put it in .env)")

    def generate(self, prompt: str, *, system: str | None = None, temperature: float = 0.0,
                 max_output_tokens: int = 256, thinking_budget: int | None = 0,
                 response_schema: dict | None = None) -> str:
        try:
            from openai import OpenAI
        except Exception as exc:  # SDK missing
            raise LLMError(f"openai SDK not installed: {exc}") from exc
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs: dict = {"model": self.model, "messages": messages, "temperature": temperature,
                        "max_tokens": max_output_tokens}
        if response_schema is not None:
            kwargs["response_format"] = {"type": "json_object"}  # guaranteed-valid JSON
        try:
            resp = OpenAI(api_key=self.api_key).chat.completions.create(**kwargs)
            return (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            raise LLMError(f"OpenAI error: {str(exc)[:200]}") from exc


def get_provider(name: str | None = None) -> LLMProvider:
    """Factory driven by ``AXIOM_LLM_PROVIDER`` (default 'gemini'). 'mock' for tests."""
    load_env()
    name = (name or os.environ.get("AXIOM_LLM_PROVIDER", "gemini")).lower()
    if name == "gemini":
        return GeminiProvider()
    if name == "openai":
        return OpenAIProvider()
    if name == "mock":
        return MockProvider()
    raise LLMError(f"unknown LLM provider {name!r} (supported: gemini, openai, mock)")
