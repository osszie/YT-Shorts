import shutil
import subprocess

import pytest

from pipeline import orchestrator
from pipeline.clip import reframe as rf
from pipeline.job import Job, STATUS_AWAITING_PUBLISH
from pipeline.media import captions


# --- reframe crop math ---------------------------------------------------

def test_crop_window_landscape_centered_on_face():
    cw, ch, cx, cy = rf.crop_window(1920, 1080, face_cx=0.5)
    assert ch == 1080
    assert abs(cw - round(1080 * 9 / 16)) <= 2
    assert cy == 0
    # centered: crop x roughly centers the window
    assert abs((cx + cw / 2) - 960) <= 2


def test_crop_window_clamps_to_frame():
    cw, ch, cx, cy = rf.crop_window(1920, 1080, face_cx=0.0)  # face at far left
    assert cx == 0
    cw, ch, cx, cy = rf.crop_window(1920, 1080, face_cx=1.0)  # far right
    assert cx == 1920 - cw


def test_crop_window_even_dimensions():
    cw, ch, _, _ = rf.crop_window(1281, 721, face_cx=0.5)
    assert cw % 2 == 0 and ch % 2 == 0


# --- caption track from words (no re-transcribe) -------------------------

def test_build_track_from_words():
    words = [{"word": "Hello", "start": 0.0, "end": 0.5},
             {"word": "world.", "start": 0.5, "end": 1.0},
             {"word": "Again", "start": 1.0, "end": 1.6}]
    track = captions.build_track_from_words(words, total=2.0)
    assert track and all({"text", "start", "end", "words"} <= set(c) for c in track)


# --- clip render stages --------------------------------------------------

def test_clip_metadata_offline(cfg):
    from pipeline.stages.clip_render import ClipMetadataStage
    job = Job.create("hidden_things", mode="clip", data={
        "clip": {"hook": "The wildest moment", "start": 0, "end": 30},
        "clip_text": "so then the whole thing fell over and everyone lost it"})
    ClipMetadataStage().run(job, cfg)
    meta = job.data["metadata"]
    assert meta["title"] == "The wildest moment"
    assert "#shorts" in meta["description"] and meta["tags"]


def test_clip_render_flow_with_mocks(cfg, monkeypatch):
    import pipeline.stages.clip_render as cr
    from pipeline.media import thumbnail as tmod

    def fake_reframe(src, s, e, out):
        open(out, "wb").write(b"x")
        return out, True
    monkeypatch.setattr(cr.rf, "reframe", fake_reframe)
    monkeypatch.setattr(cr.probe, "require", lambda _t: None)
    monkeypatch.setattr(cr.probe, "duration_seconds", lambda _p: 30.0)

    def fake_run(cmd, **kw):
        open(cmd[-1], "wb").write(b"y")  # create final.mp4 (last arg)
        class R:
            returncode = 0
            stderr = ""
        return R()
    monkeypatch.setattr(cr.subprocess, "run", fake_run)
    monkeypatch.setattr(tmod, "render", lambda *a, **k: ("t.jpg", True))

    job = Job.create("hidden_things", mode="clip", data={
        "source_path": "/x.mp4",
        "clip": {"start": 10, "end": 40, "hook": "Big moment", "score": 0.9},
        "words": [{"word": "hello", "start": 0, "end": 1}], "clip_text": "hello"})
    status = orchestrator.run_job(job, cfg, stop_before_upload=True)

    assert status == STATUS_AWAITING_PUBLISH
    assert job.data["metadata"]["title"] == "Big moment"
    assert job.data["reframe"]["face_tracked"] is True
    assert job.artifact("final.mp4").exists()


# --- real ffmpeg reframe (skipped where ffmpeg is absent, e.g. CI) --------

def test_reframe_real_center_crop(tmp_path):
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("ffmpeg/ffprobe not installed")
    from pipeline.media import probe
    src = str(tmp_path / "land.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi",
                    "-i", "testsrc=size=1280x720:rate=30:duration=3", "-pix_fmt", "yuv420p", src],
                   check=True, capture_output=True)
    out = str(tmp_path / "vert.mp4")
    rf.reframe(src, 0.5, 2.5, out)
    assert probe.dimensions(out) == (1080, 1920)
