"""Local Ollama backend — fully open-source / offline-capable ("any model").

Talks to a local Ollama server over HTTP. No web grounding (falls back to a
normal generation). Retry/backoff + pacing are applied by pipeline/llm.py.
"""
from __future__ import annotations

import json
import os

from .base import LLMUnavailable, Provider, extract_json

BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.1")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


class OllamaProvider(Provider):
    name = "ollama"

    @property
    def model(self) -> str:
        return MODEL_NAME

    def available(self) -> bool:
        # Assume a configured local server is up; a down server surfaces as a
        # connection error that the retry/fail-loud path handles.
        return bool(BASE_URL)

    def _generate(self, prompt: str, *, temperature: float, max_tokens: int, fmt: str | None = None) -> str:
        import requests
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if fmt:
            payload["format"] = fmt  # "json" → Ollama constrains output to JSON
        r = requests.post(f"{BASE_URL}/api/generate", json=payload, timeout=120)
        r.raise_for_status()
        text = (r.json().get("response") or "").strip()
        if not text:
            raise LLMUnavailable("Empty response from Ollama.")
        return text

    def generate_text(self, prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> str:
        return self._generate(prompt, temperature=temperature, max_tokens=max_tokens)

    def generate_json(self, prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> dict:
        text = self._generate(prompt, temperature=temperature, max_tokens=max_tokens, fmt="json")
        return extract_json(text)

    def embed(self, text: str) -> list[float] | None:
        import requests
        try:
            r = requests.post(f"{BASE_URL}/api/embeddings",
                              json={"model": EMBED_MODEL, "prompt": text}, timeout=60)
            r.raise_for_status()
            return r.json().get("embedding")
        except Exception:
            return None
