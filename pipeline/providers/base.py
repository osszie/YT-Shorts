"""Provider interface + shared helpers.

A Provider does the raw model call; it must NOT implement pacing/retry — that
lives once in pipeline/llm.py so every backend gets it uniformly.
"""
from __future__ import annotations

import abc
import json
import re


class LLMUnavailable(RuntimeError):
    """Raised when the backend isn't configured or a call fails hard."""


def extract_json(text: str) -> dict:
    """Best-effort JSON extraction from a model's text response."""
    cleaned = re.sub(r"```(?:json)?\s*", "", (text or "").strip())
    cleaned = cleaned.replace("```", "").strip()
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1:
        raise LLMUnavailable(f"No JSON found in model output: {cleaned[:200]}")
    frag = re.sub(r",\s*([}\]])", r"\1", cleaned[start:end + 1])
    return json.loads(frag)


class Provider(abc.ABC):
    """One LLM backend. Subclasses implement available() + generate_text(); the
    rest have sensible defaults."""

    name = "base"

    @abc.abstractmethod
    def available(self) -> bool:
        ...

    @abc.abstractmethod
    def generate_text(self, prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> str:
        ...

    def generate_json(self, prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> dict:
        return extract_json(self.generate_text(prompt, temperature=temperature, max_tokens=max_tokens))

    def generate_grounded(self, prompt: str, *, temperature: float = 0.9,
                          max_tokens: int = 2048) -> tuple[str, list[str]]:
        # Most backends can't web-search; degrade to a normal generation.
        return self.generate_text(prompt, temperature=temperature, max_tokens=max_tokens), []

    def embed(self, text: str) -> list[float] | None:
        return None

    @property
    def model(self) -> str:
        return ""
