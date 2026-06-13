from pipeline import doctor


def test_run_checks_has_expected_groups():
    groups = doctor.run_checks()
    assert {"Config", "Python packages", "Binaries", "Render engine",
            "Backgrounds", "LLM", "Upload"} <= set(groups)


def test_config_checks_pass():
    out = doctor._check_config()
    assert out and all(status == doctor.OK for _, status, _ in out)


def test_missing_ffmpeg_is_a_fail(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    bins = doctor._check_binaries()
    assert all(status == doctor.FAIL for _, status, _ in bins)


def test_llm_check_reflects_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    assert doctor._check_llm()[0][1] == doctor.OK
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert doctor._check_llm()[0][1] == doctor.WARN


def test_summarize_blocks_on_fail():
    groups = {"g": [("ffmpeg", doctor.FAIL, ""), ("x", doctor.OK, "")]}
    s = doctor.summarize(groups)
    assert s["ready"] is False and "ffmpeg" in s["fails"]


def test_summarize_ready_with_only_warns():
    groups = {"g": [("a", doctor.OK, ""), ("b", doctor.WARN, "")]}
    s = doctor.summarize(groups)
    assert s["ready"] is True and "b" in s["warns"]
