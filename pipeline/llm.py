"""LLM access — one API, swappable backend (STRATEGY.md §8 "any model").

A thin facade over a selected Provider (Gemini by default, local Ollama, ...),
chosen by LLM_PROVIDER. This module owns the cross-cutting concerns — pacing and
retry/backoff on transient rate limits — so every backend gets them and every
stage keeps calling the same `llm.generate_text/json/grounded/embed` + `available`.
Offline (no key / no server) the calls raise and callers fall back to
deterministic behaviour (the spine).
"""
from __future__ import annotations

import os
import random
import time

from dotenv import load_dotenv

from . import ROOT
from .providers.base import LLMUnavailable, extract_json  # re-exported for back-compat

load_dotenv(dotenv_path=str(ROOT / ".env"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
# Back-compat / display: the active model name (Gemini or Ollama).
MODEL_NAME = (os.getenv("OLLAMA_MODEL", "llama3.1") if LLM_PROVIDER == "ollama"
              else os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # referenced by some callers/tests

# Rate-limit resilience (esp. free tiers): retry transient 429/503 with backoff
# and pace calls to glide under per-minute caps. Provider-agnostic.
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "5"))
RETRY_BASE = float(os.getenv("GEMINI_RETRY_BASE", "2.0"))
RETRY_CAP = float(os.getenv("GEMINI_RETRY_CAP", "60.0"))
MIN_INTERVAL = float(os.getenv("GEMINI_MIN_INTERVAL", "4.0"))
_RETRYABLE = ("429", "resourceexhausted", "resource exhausted", "rate limit",
              "quota", "exceeded", "503", "unavailable", "deadline", "500")
_last_call = 0.0

_extract_json = extract_json  # back-compat alias
_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        if LLM_PROVIDER == "ollama":
            from .providers.ollama import OllamaProvider
            _provider = OllamaProvider()
        else:
            from .providers.gemini import GeminiProvider
            _provider = GeminiProvider()
    return _provider


def active_model() -> str:
    try:
        return _get_provider().model or MODEL_NAME
    except Exception:
        return MODEL_NAME


def available() -> bool:
    try:
        return _get_provider().available()
    except Exception:
        return False


def is_retryable(e: Exception) -> bool:
    s = str(e).lower()
    return any(tok in s for tok in _RETRYABLE)


def _retry_delay(e: Exception, attempt: int) -> float:
    import re
    m = (re.search(r"retry_delay\s*\{?\s*seconds:\s*(\d+)", str(e))
         or re.search(r"retry in (\d+(?:\.\d+)?)\s*s", str(e), re.I))
    if m:
        return min(RETRY_CAP, float(m.group(1)) + 1.0)
    return min(RETRY_CAP, RETRY_BASE * (2 ** attempt)) + random.uniform(0, 0.75)


def _pace():
    """Sleep just enough to keep >= MIN_INTERVAL seconds between calls."""
    global _last_call
    if MIN_INTERVAL > 0:
        wait = _last_call + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
    _last_call = time.monotonic()


def _call(fn):
    """Run a backend call with pacing + retry/backoff on transient rate limits."""
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            _pace()
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < MAX_RETRIES and is_retryable(e):
                delay = _retry_delay(e, attempt)
                print(f"  ⏳ {LLM_PROVIDER} rate-limited; retrying in {delay:.0f}s "
                      f"[{attempt + 1}/{MAX_RETRIES}]")
                time.sleep(delay)
                continue
            raise
    raise last  # pragma: no cover


def generate_text(prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> str:
    return _call(lambda: _get_provider().generate_text(prompt, temperature=temperature, max_tokens=max_tokens))


def generate_json(prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> dict:
    return _call(lambda: _get_provider().generate_json(prompt, temperature=temperature, max_tokens=max_tokens))


def generate_grounded(prompt: str, *, temperature: float = 0.9, max_tokens: int = 2048) -> tuple[str, list[str]]:
    return _call(lambda: _get_provider().generate_grounded(prompt, temperature=temperature, max_tokens=max_tokens))


def embed(text: str) -> list[float] | None:
    try:
        return _call(lambda: _get_provider().embed(text))
    except Exception:
        return None
