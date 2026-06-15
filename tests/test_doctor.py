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


# --- live Gemini probe ---------------------------------------------------

def test_probe_skips_without_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    name, status, detail = doctor.probe_llm()
    assert status == doctor.WARN and "no GOOGLE_API_KEY" in detail


def test_probe_reports_ok_on_success(monkeypatch):
    import pipeline.llm as llm
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    monkeypatch.setattr(doctor, "_have", lambda _m: True)
    monkeypatch.setattr(llm, "generate_text", lambda *a, **k: "ok")
    name, status, detail = doctor.probe_llm()
    assert status == doctor.OK and "reachable" in detail


def test_probe_classifies_rate_limit_as_warn(monkeypatch):
    import pipeline.llm as llm
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    monkeypatch.setattr(doctor, "_have", lambda _m: True)

    def boom(*a, **k):
        raise RuntimeError("429 RESOURCE_EXHAUSTED: You exceeded your current quota")
    monkeypatch.setattr(llm, "generate_text", boom)
    name, status, detail = doctor.probe_llm()
    assert status == doctor.WARN and ("rate-limited" in detail or "quota" in detail)


def test_probe_never_fails_hard(monkeypatch):
    import pipeline.llm as llm
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    monkeypatch.setattr(doctor, "_have", lambda _m: True)
    monkeypatch.setattr(llm, "generate_text", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("403 invalid api key")))
    name, status, detail = doctor.probe_llm()
    assert status == doctor.WARN  # never FAIL — offline spine still works


def test_run_checks_probe_adds_live_row(monkeypatch):
    import pipeline.llm as llm
    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    monkeypatch.setattr(doctor, "_have", lambda _m: True)
    monkeypatch.setattr(llm, "generate_text", lambda *a, **k: "ok")
    groups = doctor.run_checks(probe=True)
    assert any(n == "Gemini live probe" for n, _, _ in groups["LLM"])
    # default (no probe) does not make a call
    assert all(n != "Gemini live probe" for n, _, _ in doctor.run_checks()["LLM"])
