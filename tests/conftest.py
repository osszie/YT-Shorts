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


@pytest.fixture
def stub_media(monkeypatch):
    """Replace the media stages (which need ffmpeg/edge-tts/whisper/Node) with
    bookkeeping no-ops, so orchestration + CLI logic can be tested end-to-end."""
    from pipeline.stages.voice import VoiceStage
    from pipeline.stages.captions import CaptionsStage
    from pipeline.stages.assemble import AssembleStage
    from pipeline.stages.thumbnail import ThumbnailStage
    from pipeline.stages.upload import UploadStage

    def make(name):
        def run(self, job, cfg):
            job.data[f"{name}_done"] = True
            job.mark_stage(name)

        def done(self, job):
            return job.data.get(f"{name}_done", False)
        return run, done

    for cls, name in [(VoiceStage, "voice"), (CaptionsStage, "captions"),
                      (AssembleStage, "assemble"), (ThumbnailStage, "thumbnail"),
                      (UploadStage, "upload")]:
        run, done = make(name)
        monkeypatch.setattr(cls, "run", run)
        monkeypatch.setattr(cls, "done", done)
