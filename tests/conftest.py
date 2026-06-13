"""Shared fixtures. Every test runs fully offline: no Gemini key, no ffmpeg, no
network — the pipeline's deterministic fallbacks are exercised. Job state and the
similarity catalog are redirected into a temp dir so tests never touch the repo's
real jobs/ or catalog/.
"""
import pytest

import pipeline.job as job_mod
import pipeline.similarity as sim_mod
import pipeline.llm as llm_mod


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(job_mod, "JOBS_DIR", tmp_path / "jobs")
    monkeypatch.setattr(sim_mod, "CATALOG_PATH", tmp_path / "catalog" / "embeddings.json")
    # Force offline so no test accidentally reaches the network / an API key.
    monkeypatch.setattr(llm_mod, "GOOGLE_API_KEY", None, raising=False)
    monkeypatch.setattr(llm_mod, "available", lambda: False)
    monkeypatch.setattr(sim_mod.llm, "embed", lambda text: None)
    yield


@pytest.fixture
def cfg():
    from pipeline.config import load_config
    return load_config("hidden_things")
