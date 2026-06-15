import pytest

import pipeline.llm as llm
from pipeline.job import Job
from pipeline.stages.angle import AngleStage
from pipeline.stages.script import ScriptStage


def _boom(*_a, **_k):
    raise RuntimeError("429 RESOURCE_EXHAUSTED: You exceeded your current quota")


# --- retry / backoff -----------------------------------------------------

def test_is_retryable_classification():
    assert llm.is_retryable(Exception("429 quota exceeded"))
    assert llm.is_retryable(Exception("503 Service Unavailable"))
    assert not llm.is_retryable(Exception("400 invalid argument"))


def test_call_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)  # no real waiting
    monkeypatch.setattr(llm, "MAX_RETRIES", 4)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("429 quota exceeded")
        return "ok"

    assert llm._call(flaky) == "ok"
    assert calls["n"] == 3


def test_call_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)
    monkeypatch.setattr(llm, "MAX_RETRIES", 2)
    with pytest.raises(RuntimeError):
        llm._call(_boom)


def test_call_does_not_retry_non_retryable(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda _s: None)
    calls = {"n": 0}

    def bad():
        calls["n"] += 1
        raise ValueError("400 bad request")

    with pytest.raises(ValueError):
        llm._call(bad)
    assert calls["n"] == 1  # tried once, no retries


# --- fail loud, never garbage (configured-but-failing LLM) ---------------

def test_angle_offline_fallback_has_no_scaffolding(cfg):
    # Offline (no key) is the only place fallbacks run; they must be clean prose,
    # not leaked lens/format prompt text.
    job = Job.create("hidden_things")
    job.data["subject"] = "the dimples on a golf ball"
    job.data["lens_domain"] = "engineering"
    AngleStage().run(job, cfg)
    text = " ".join(job.data["angle_candidates"]).lower()
    assert "applied to" not in text
    assert "identify a common assumption" not in text
    assert "imagine if this didn't exist" not in text


def test_angle_fails_loud_when_configured_but_erroring(cfg, monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "generate_json", _boom)
    job = Job.create("hidden_things")
    job.data["subject"] = "x"
    job.data["lens_domain"] = "engineering"
    with pytest.raises(Exception):
        AngleStage().run(job, cfg)


def test_script_fails_loud_when_configured_but_erroring(cfg, monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "generate_text", _boom)
    monkeypatch.setattr(llm, "generate_grounded", _boom)
    job = Job.create("hidden_things")
    job.data.update(subject="x", angle="a thesis", format=cfg.format_ids[0])
    with pytest.raises(Exception):
        ScriptStage().run(job, cfg)
