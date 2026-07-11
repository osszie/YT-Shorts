from pipeline.job import (Job, STATUS_AWAITING_ANGLE, STATUS_AWAITING_PUBLISH,
                          STATUS_DONE)
from pipeline import orchestrator


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
    assert job.data.get("thumbnail_done")  # thumbnail built before the publish gate
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


def test_failure_during_regen_marks_job_failed(cfg, monkeypatch, stub_media):
    """A rate-limit inside the similarity-regen loop must fail the job cleanly,
    not escape run_job as an uncaught exception."""
    from pipeline.stages.script import ScriptStage
    from pipeline.stages.similarity_guard import SimilarityGuardStage
    from pipeline.stages.base import SimilarityTooHigh

    calls = {"n": 0}

    def script_run(self, job, _cfg):
        calls["n"] += 1
        if calls["n"] == 1:
            job.data["script"] = "first attempt"
            job.mark_stage("script")
        else:
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota")
    monkeypatch.setattr(ScriptStage, "run", script_run)
    monkeypatch.setattr(SimilarityGuardStage, "run",
                        lambda self, job, _cfg: (_ for _ in ()).throw(SimilarityTooHigh(0.99, "other")))

    job = Job.create("hidden_things")
    orchestrator.run_job(job, cfg, stop_before_upload=True)   # park at angle gate
    job.approve_gate("angle"); job.save()
    status = orchestrator.run_job(job, cfg, stop_before_upload=True)
    assert status == "failed"
    assert "regen" in (job.error or "")
