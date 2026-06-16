"""Google Gemini backend (the project's default).

Uses the REST transport by default so it works behind TLS-intercepting proxies.
Retry/backoff and pacing are applied by pipeline/llm.py, not here.
"""
from __future__ import annotations

import os

from .base import LLMUnavailable, Provider, extract_json

API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")
TRANSPORT = os.getenv("GEMINI_TRANSPORT", "rest")


class GeminiProvider(Provider):
    name = "gemini"
    _configured = False

    @property
    def model(self) -> str:
        return MODEL_NAME

    def available(self) -> bool:
        return bool(API_KEY)

    def _ensure(self):
        if not API_KEY:
            raise LLMUnavailable("GOOGLE_API_KEY is not set; running in offline/fallback mode.")
        if not GeminiProvider._configured:
            import google.generativeai as genai
            genai.configure(api_key=API_KEY, transport=TRANSPORT)
            GeminiProvider._configured = True

    def generate_text(self, prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> str:
        self._ensure()
        import google.generativeai as genai
        from google.generativeai.types import RequestOptions
        model = genai.GenerativeModel(model_name=MODEL_NAME, generation_config={
            "temperature": temperature, "top_p": 0.95, "top_k": 40, "max_output_tokens": max_tokens})
        resp = model.generate_content(prompt, request_options=RequestOptions(timeout=90))
        if not resp.text or not resp.text.strip():
            raise LLMUnavailable("Empty response from Gemini.")
        return resp.text

    def generate_json(self, prompt: str, *, temperature: float = 1.0, max_tokens: int = 2048) -> dict:
        self._ensure()
        import google.generativeai as genai
        from google.generativeai.types import RequestOptions
        model = genai.GenerativeModel(model_name=MODEL_NAME, generation_config={
            "temperature": temperature, "top_p": 0.95, "top_k": 40,
            "max_output_tokens": max_tokens, "response_mime_type": "application/json"})
        try:
            resp = model.generate_content(prompt, request_options=RequestOptions(timeout=90))
            return extract_json(resp.text)
        except Exception as e:
            from ..llm import is_retryable
            if is_retryable(e):
                raise  # already paced/retried upstream; surface so the stage can fail/retry
            return extract_json(self.generate_text(prompt, temperature=temperature, max_tokens=max_tokens))

    def generate_grounded(self, prompt: str, *, temperature: float = 0.9,
                          max_tokens: int = 2048) -> tuple[str, list[str]]:
        self._ensure()
        import google.generativeai as genai
        from google.generativeai.types import RequestOptions
        from ..llm import is_retryable
        for tool in ("google_search_retrieval", "google_search"):
            try:
                model = genai.GenerativeModel(
                    model_name=MODEL_NAME,
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                    tools=tool)
                resp = model.generate_content(prompt, request_options=RequestOptions(timeout=120))
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
                    raise
                continue
        return self.generate_text(prompt, temperature=temperature, max_tokens=max_tokens), []

    def embed(self, text: str) -> list[float] | None:
        if not API_KEY:
            return None
        self._ensure()
        import google.generativeai as genai
        res = genai.embed_content(model=EMBED_MODEL, content=text, task_type="semantic_similarity")
        return res["embedding"]
