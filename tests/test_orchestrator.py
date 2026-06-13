import pytest

from pipeline.job import (Job, STATUS_AWAITING_ANGLE, STATUS_AWAITING_PUBLISH,
                          STATUS_DONE)
from pipeline import orchestrator
from pipeline.stages.voice import VoiceStage
from pipeline.stages.captions import CaptionsStage
from pipeline.stages.assemble import AssembleStage
from pipeline.stages.upload import UploadStage


@pytest.fixture
def stub_media(monkeypatch):
    """Replace the media stages (which need ffmpeg/edge-tts/whisper/Node) with
    bookkeeping no-ops, so the orchestration logic can be tested end-to-end."""
    def make(name):
        def run(self, job, cfg):
            job.data[f"{name}_done"] = True
            job.mark_stage(name)

        def done(self, job):
            return job.data.get(f"{name}_done", False)
        return run, done

    for cls, name in [(VoiceStage, "voice"), (CaptionsStage, "captions"),
                      (AssembleStage, "assemble"), (UploadStage, "upload")]:
        run, done = make(name)
        monkeypatch.setattr(cls, "run", run)
        monkeypatch.setattr(cls, "done", done)


def test_parks_at_angle_gate_before_script(cfg, stub_media):
    job = Job.create("hidden_things")
    status = orchestrator.run_job(job, cfg, stop_before_upload=True)
    assert status == STATUS_AWAITING_ANGLE
    assert job.data.get("subject")        # idea + angle ran
    assert "script" not in job.data       # but script must wait for the gate


def test_full_flow_through_both_gates(cfg, stub_media):
    job = Job.create("hidden_things")
    orchestrator.run_job(job, cfg, stop_before_upload=True)

    job.approve_gate("angle"); job.save()
    status = orchestrator.run_job(job, cfg, stop_before_upload=True)
    assert status == STATUS_AWAITING_PUBLISH
    assert job.data.get("metadata")
    assert job.data.get("voice_done") and job.data.get("assemble_done")
    assert "upload_done" not in job.data   # upload waits behind the publish gate

    job.approve_gate("publish"); job.save()
    status = orchestrator.run_job(job, cfg, stop_before_upload=False)
    assert status == STATUS_DONE
    assert job.data.get("upload_done")


def test_idempotent_rerun_keeps_subject(cfg, stub_media):
    job = Job.create("hidden_things")
    orchestrator.run_job(job, cfg, stop_before_upload=True)
    subject = job.data["subject"]
    orchestrator.run_job(job, cfg, stop_before_upload=True)
    assert job.data["subject"] == subject


def test_failure_is_recorded_and_resumable(cfg, monkeypatch):
    """A stage raising should park the job as failed with the cause, not crash."""
    from pipeline.stages.script import ScriptStage

    def boom(self, job, cfg):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(ScriptStage, "run", boom)

    job = Job.create("hidden_things")
    orchestrator.run_job(job, cfg, stop_before_upload=True)
    job.approve_gate("angle"); job.save()
    status = orchestrator.run_job(job, cfg, stop_before_upload=True)
    assert status == "failed"
    assert "kaboom" in (job.error or "")
