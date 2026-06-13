from pipeline.job import (Job, all_jobs, recent_subjects, STATUS_ACTIVE,
                          STATUS_AWAITING_ANGLE)


def test_create_persists_and_loads():
    job = Job.create("hidden_things")
    assert job.status == STATUS_ACTIVE
    assert job.stage == "created"
    assert (job.dir / "job.json").exists()

    reloaded = Job.load(job.id)
    assert reloaded.id == job.id
    assert reloaded.niche == "hidden_things"


def test_save_load_roundtrip_preserves_state():
    job = Job.create("hidden_things")
    job.data["subject"] = "the dimples on a golf ball"
    job.approve_gate("angle", note="picked #2")
    job.save()

    reloaded = Job.load(job.id)
    assert reloaded.data["subject"] == "the dimples on a golf ball"
    assert reloaded.gate_approved("angle") is True
    assert any(h["stage"] == "gate:angle" for h in reloaded.history)


def test_gate_defaults_unapproved():
    job = Job.create("hidden_things")
    assert job.gate_approved("angle") is False
    assert job.gate_approved("publish") is False


def test_recent_subjects_dedupes_and_orders():
    a = Job.create("hidden_things"); a.data["subject"] = "golf ball dimples"; a.save()
    b = Job.create("hidden_things"); b.data["subject"] = "airport carpet"; b.save()
    c = Job.create("hidden_things"); c.data["subject"] = "Golf Ball Dimples"; c.save()  # dup (case)

    subs = recent_subjects()
    # Deduped case-insensitively; most-recent first.
    assert subs[0] in ("Golf Ball Dimples", "airport carpet")
    lowered = [s.lower() for s in subs]
    assert lowered.count("golf ball dimples") == 1
    assert "airport carpet" in lowered


def test_recent_subjects_excludes_self():
    a = Job.create("hidden_things"); a.data["subject"] = "brick holes"; a.save()
    b = Job.create("hidden_things"); b.data["subject"] = "pencil paint"; b.save()
    assert "brick holes" not in recent_subjects(exclude_job_id=a.id)
    assert "pencil paint" in [s.lower() for s in recent_subjects(exclude_job_id=a.id)] \
        or "pencil paint" in recent_subjects(exclude_job_id=a.id)


def test_all_jobs_empty_when_none():
    assert all_jobs() == []
