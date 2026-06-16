import argparse

import cli
from pipeline import orchestrator
from pipeline.clip import highlight as hl
from pipeline.job import Job, all_jobs, STATUS_AWAITING_CLIP, STATUS_DONE


def _stub_source(monkeypatch):
    """Avoid ffprobe + Whisper so clip-source tests run anywhere (incl. CI)."""
    import pipeline.stages.clip as clipstage
    monkeypatch.setattr(clipstage.probe, "require", lambda _t: None)
    monkeypatch.setattr(clipstage.probe, "duration_seconds", lambda _p: 90.0)
    monkeypatch.setattr(clipstage.tr, "transcribe", lambda _p: {
        "duration": 90.0, "text": "hello world",
        "words": [{"word": "hello", "start": 0.0, "end": 1.0},
                  {"word": "world.", "start": 1.0, "end": 2.0}]})


# --- highlight selection -------------------------------------------------

def test_evenly_spaced_offline():
    clips = hl._evenly_spaced(120.0, 3)
    assert 1 <= len(clips) <= 3
    for c in clips:
        assert 0 <= c["start"] < c["end"] <= 120.0


def test_sanitize_caps_length():
    out = hl._sanitize([{"start": 10, "end": 1000, "score": 0.9, "hook": "x"}],
                       duration=300, min_len=18, max_len=60)
    assert out and (out[0]["end"] - out[0]["start"]) <= 60


def test_select_highlights_uses_llm(monkeypatch):
    import pipeline.clip.highlight as H
    monkeypatch.setattr(H.llm, "available", lambda: True)
    monkeypatch.setattr(H.llm, "generate_json", lambda *a, **k: {"clips": [
        {"start": 5, "end": 35, "hook": "Great bit", "reason": "funny", "score": 0.9}]})
    transcript = {"duration": 120.0, "text": "hi",
                  "words": [{"word": "hi", "start": 0, "end": 1}]}
    clips = H.select_highlights(transcript, count=3)
    assert clips and clips[0]["hook"] == "Great bit"


def test_select_highlights_offline_fallback(monkeypatch):
    transcript = {"duration": 120.0, "text": "hi",
                  "words": [{"word": "hi", "start": 0, "end": 1}]}
    clips = hl.select_highlights(transcript, count=2)  # llm.available() False (conftest)
    assert 1 <= len(clips) <= 2


# --- source pipeline + gate ---------------------------------------------

def test_clip_source_parks_at_clip_gate(cfg, monkeypatch):
    _stub_source(monkeypatch)
    job = Job.create("hidden_things", mode="clip_source",
                     data={"source_path": __file__, "want_clips": 2})
    status = orchestrator.run_job(job, cfg)
    assert status == STATUS_AWAITING_CLIP
    assert job.data["clips_proposed"]
    assert (job.dir / "transcript.json").exists()


def test_clip_gate_then_done(cfg, monkeypatch):
    _stub_source(monkeypatch)
    job = Job.create("hidden_things", mode="clip_source",
                     data={"source_path": __file__, "want_clips": 2})
    orchestrator.run_job(job, cfg)
    job.approve_gate("clip"); job.save()
    assert orchestrator.run_job(job, cfg) == STATUS_DONE


def test_cli_approve_clip_fans_out(cfg, monkeypatch):
    _stub_source(monkeypatch)
    cli.cmd_clip(argparse.Namespace(video=__file__, niche="hidden_things", count=2))
    src = [j for j in all_jobs() if j.mode == "clip_source"][0]
    cli.cmd_approve_clip(argparse.Namespace(job_id=src.id, pick=None))
    clip_jobs = [j for j in all_jobs() if j.mode == "clip"]
    assert len(clip_jobs) >= 1
    assert clip_jobs[0].data["clip"]["end"] > clip_jobs[0].data["clip"]["start"]
