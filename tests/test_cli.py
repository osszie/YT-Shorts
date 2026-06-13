import argparse

import cli
from pipeline.job import Job, all_jobs, STATUS_AWAITING_ANGLE, STATUS_AWAITING_PUBLISH


def ns(**kw):
    return argparse.Namespace(**kw)


def test_new_creates_jobs_parked_at_angle_gate(cfg):
    # `new` runs only idea + angle, then parks — no media deps needed.
    rc = cli.cmd_new(ns(niche="hidden_things", count=2))
    assert rc == 0
    jobs = all_jobs()
    assert len(jobs) == 2
    assert all(j.status == STATUS_AWAITING_ANGLE for j in jobs)
    assert all(j.data.get("angle_candidates") for j in jobs)


def test_approve_angle_pick_selects_candidate(cfg, stub_media):
    cli.cmd_new(ns(niche="hidden_things", count=1))
    job = all_jobs()[0]
    rc = cli.cmd_approve_angle(ns(job_id=job.id, all=False, pick=2, edit=None))
    assert rc == 0
    reloaded = Job.load(job.id)
    assert reloaded.gate_approved("angle")
    assert reloaded.data["angle"] == reloaded.data["angle_candidates"][1]
    # With media stubbed, it advances all the way to the publish gate.
    assert reloaded.status == STATUS_AWAITING_PUBLISH


def test_approve_angle_edit_overrides_text(cfg, stub_media):
    cli.cmd_new(ns(niche="hidden_things", count=1))
    job = all_jobs()[0]
    cli.cmd_approve_angle(ns(job_id=job.id, all=False, pick=None, edit="a totally custom angle"))
    assert Job.load(job.id).data["angle"] == "a totally custom angle"


def test_approve_publish_uploads_after_gate(cfg, stub_media):
    cli.cmd_new(ns(niche="hidden_things", count=1))
    job = all_jobs()[0]
    cli.cmd_approve_angle(ns(job_id=job.id, all=False, pick=None, edit=None))
    rc = cli.cmd_approve_publish(ns(job_id=job.id, all=False))
    assert rc == 0
    reloaded = Job.load(job.id)
    assert reloaded.gate_approved("publish")
    assert reloaded.data.get("upload_done") is True


def test_status_and_niches_run(cfg, capsys):
    cli.cmd_new(ns(niche="hidden_things", count=1))
    assert cli.cmd_status(ns()) == 0
    assert cli.cmd_niches(ns()) == 0
    out = capsys.readouterr().out
    assert "hidden_things" in out


def test_doctor_command_returns_int(cfg):
    rc = cli.cmd_doctor(ns())
    assert rc in (0, 1)  # 1 if this env is missing ffmpeg/backgrounds, which is fine
