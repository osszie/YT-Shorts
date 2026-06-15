"""LLM access — one model, distinct prompt per stage (STRATEGY.md §4).

Wraps Google Gemini for: plain text, JSON, grounded JSON (web-search backed for
real, current facts), and embeddings (for the similarity guard). Everything
degrades gracefully: if GOOGLE_API_KEY is missing the calls raise
LLMUnavailable, and callers fall back to deterministic behaviour so the pipeline
"spine" still runs offline (STRATEGY.md §5, MVP step 1).
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import re
import time

from dotenv import load_dotenv

from . import ROOT

load_dotenv(dotenv_path=str(ROOT / ".env"))

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")
# Default to the REST transport: the gRPC client uses its own root store and
# fails behind TLS-intercepting proxies (managed/corporate networks) with
# CERTIFICATE_VERIFY_FAILED, whereas REST goes through the system-trusted HTTPS
# stack. Override with GEMINI_TRANSPORT=grpc if you prefer it.
TRANSPORT = os.getenv("GEMINI_TRANSPORT", "rest")

# Rate-limit resilience. Gemini's free tier has a low requests-per-minute cap, so
# a batch quickly hits HTTP 429 and (without this) every stage falls back to
# templates. Retry transient 429/503 with exponential backoff, honouring a
# server-suggested retry_delay when present, before giving up.
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "5"))
RETRY_BASE = float(os.getenv("GEMINI_RETRY_BASE", "2.0"))
RETRY_CAP = float(os.getenv("GEMINI_RETRY_CAP", "60.0"))
# Proactive pacing: keep at least this many seconds between calls so a batch
# glides under the free tier's requests-per-minute cap instead of bursting into
# 429s and waiting out the backoff. Set GEMINI_MIN_INTERVAL=0 on a paid tier.
MIN_INTERVAL = float(os.getenv("GEMINI_MIN_INTERVAL", "4.0"))
_RETRYABLE = ("429", "resourceexhausted", "resource exhausted", "rate limit",
              "quota", "exceeded", "503", "unavailable", "deadline", "500")
_last_call = 0.0


class LLMUnavailable(RuntimeError):
    """Raised when no API key is configured or the API call fails hard."""


_configured = False


def available() -> bool:
    return bool(GOOGLE_API_KEY)


def is_retryable(e: Exception) -> bool:
    """True for transient rate-limit / availability errors worth retrying."""
    s = str(e).lower()
    return any(tok in s for tok in _RETRYABLE)


def _retry_delay(e: Exception, attempt: int) -> float:
    m = (re.search(r"retry_delay\s*\{?\s*seconds:\s*(\d+)", str(e))
         or re.search(r"retry in (\d+(?:\.\d+)?)\s*s", str(e), re.I))
    if m:
        return min(RETRY_CAP, float(m.group(1)) + 1.0)
    return min(RETRY_CAP, RETRY_BASE * (2 ** attempt)) + random.uniform(0, 0.75)


def _pace():
    """Sleep just enough to keep >= MIN_INTERVAL seconds between Gemini calls."""
    global _last_call
    if MIN_INTERVAL > 0:
        wait = _last_call + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            time.sleep(wait)
    _last_call = time.monotonic()


def _call(fn):
    """Run a Gemini call with pacing + retry/backoff on transient rate limits."""
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            _pace()
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < MAX_RETRIES and is_retryable(e):
                delay = _retry_delay(e, attempt)
                print(f"  ⏳ Gemini rate-limited (429); retrying in {delay:.0f}s "
                      f"[{attempt + 1}/{MAX_RETRIES}]")
                time.sleep(delay)
                continue
            raise
    raise last  # pragma: no cover


def _ensure_configured():
    global _configured
    if not GOOGLE_API_KEY:
        raise LLMUnavailable("GOOGLE_API_KEY is not set; running in offline/fallback mode.")
    if not _configured:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY, transport=TRANSPORT)
        _configured = True


def _extract_json(text: str) -> dict:
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


def generate_text(prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> str:
    _ensure_configured()
    import google.generativeai as genai
    from google.generativeai.types import RequestOptions

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": max_tokens,
        },
    )
    resp = _call(lambda: model.generate_content(prompt, request_options=RequestOptions(timeout=90)))
    if not resp.text or not resp.text.strip():
        raise LLMUnavailable("Empty response from Gemini.")
    return resp.text


def generate_json(prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> dict:
    _ensure_configured()
    import google.generativeai as genai
    from google.generativeai.types import RequestOptions

    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "temperature": temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": max_tokens,
            "response_mime_type": "application/json",
        },
    )
    try:
        resp = _call(lambda: model.generate_content(prompt, request_options=RequestOptions(timeout=90)))
        return _extract_json(resp.text)
    except Exception as e:
        if is_retryable(e):
            raise  # already retried; surface so the stage can fail/retry the job
        # Some models reject JSON mode; retry as plain text and parse.
        return _extract_json(generate_text(prompt, temperature=temperature, max_tokens=max_tokens))


def generate_grounded(prompt: str, *, temperature: float = 0.9, max_tokens: int = 2048) -> tuple[str, list[str]]:
    """Generate text grounded in a live web search, returning (text, sources).

    "Ground in real sources" (STRATEGY.md §2): specificity reads as researched,
    not generated — and keeps it true. Falls back to ungrounded generation if the
    grounding tool is unavailable for the configured model.
    """
    _ensure_configured()
    import google.generativeai as genai
    from google.generativeai.types import RequestOptions

    for tool in ("google_search_retrieval", "google_search"):
        try:
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                tools=tool,
            )
            resp = _call(lambda: model.generate_content(prompt, request_options=RequestOptions(timeout=120)))
            sources: list[str] = []
            try:
                for cand in resp.candidates:
                    meta = getattr(cand, "grounding_metadata", None)
                    for chunk in getattr(meta, "grounding_chunks", []) or []:
                        uri = getattr(getattr(chunk, "web", None), "uri", None)
                        if uri:
                            sources.append(uri)
            except Exception:
                pass
            if resp.text and resp.text.strip():
                return resp.text, sources
        except Exception as e:
            if is_retryable(e):
                raise  # rate-limited after retries; let the stage fail/retry the job
            continue   # this grounding tool isn't supported; try the next / ungrounded
    # Grounding tool unavailable for this model — degrade to a normal generation.
    return generate_text(prompt, temperature=temperature, max_tokens=max_tokens), []


def embed(text: str) -> list[float] | None:
    """Embed text for the similarity guard. Returns None if unavailable."""
    if not GOOGLE_API_KEY:
        return None
    try:
        _ensure_configured()
        import google.generativeai as genai
        res = _call(lambda: genai.embed_content(
            model=EMBED_MODEL, content=text, task_type="semantic_similarity"))
        return res["embedding"]
    except Exception:
        return None
