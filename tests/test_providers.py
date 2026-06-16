import sys
import types

import pipeline.llm as llm
from pipeline.providers.base import extract_json
from pipeline.providers.gemini import GeminiProvider
from pipeline.providers import gemini as gmod
from pipeline.providers.ollama import OllamaProvider


def test_extract_json_handles_fences_and_noise():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('blah {"x": "y",} trailing')["x"] == "y"


def test_gemini_available_reflects_key(monkeypatch):
    monkeypatch.setattr(gmod, "API_KEY", "")
    assert GeminiProvider().available() is False
    monkeypatch.setattr(gmod, "API_KEY", "k")
    assert GeminiProvider().available() is True


def _fake_requests(response_json, captured=None):
    fake = types.ModuleType("requests")

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return response_json

    def post(url, json=None, timeout=None):
        if captured is not None:
            captured["url"] = url
            captured["payload"] = json
        return FakeResp()

    fake.post = post
    return fake


def test_ollama_generate_text(monkeypatch):
    captured = {}
    monkeypatch.setitem(sys.modules, "requests",
                        _fake_requests({"response": "hello from ollama"}, captured))
    out = OllamaProvider().generate_text("hi")
    assert out == "hello from ollama"
    assert captured["url"].endswith("/api/generate")


def test_ollama_generate_json_uses_format(monkeypatch):
    captured = {}
    monkeypatch.setitem(sys.modules, "requests",
                        _fake_requests({"response": '{"k": "v"}'}, captured))
    assert OllamaProvider().generate_json("hi") == {"k": "v"}
    assert captured["payload"]["format"] == "json"


def test_ollama_available_when_configured():
    assert OllamaProvider().available() is True


def test_provider_selection(monkeypatch):
    monkeypatch.setattr(llm, "_provider", None)
    monkeypatch.setattr(llm, "LLM_PROVIDER", "gemini")
    assert llm._get_provider().name == "gemini"

    monkeypatch.setattr(llm, "_provider", None)
    monkeypatch.setattr(llm, "LLM_PROVIDER", "ollama")
    assert llm._get_provider().name == "ollama"
    monkeypatch.setattr(llm, "_provider", None)  # reset cache for other tests


def test_facade_generate_text_delegates_to_provider(monkeypatch):
    class FakeProvider:
        name = "fake"
        model = "fake-1"

        def available(self):
            return True

        def generate_text(self, prompt, *, temperature=1.0, max_tokens=2048):
            return f"echo:{prompt}"

    monkeypatch.setattr(llm, "_provider", FakeProvider())
    monkeypatch.setattr(llm, "MIN_INTERVAL", 0.0)  # no pacing sleep
    assert llm.generate_text("hi") == "echo:hi"
    monkeypatch.setattr(llm, "_provider", None)
