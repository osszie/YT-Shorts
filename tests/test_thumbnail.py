from pipeline.media import thumbnail
from pipeline.job import Job
from pipeline.stages.thumbnail import ThumbnailStage


def test_headline_from_subject_strips_filler():
    h = thumbnail.headline_from_subject("the dimples on a golf ball")
    assert "THE" not in h.split() and "ON" not in h.split()
    assert "GOLF" in h and h == h.upper()


def test_wrap_respects_limits():
    lines = thumbnail.wrap("DIMPLES GOLF BALL DRAG", max_chars=10, max_lines=2)
    assert len(lines) <= 2
    assert all(len(l) <= 10 or len(l.split()) == 1 for l in lines)


def test_build_filter_has_drawtext_per_line_and_label(cfg):
    style = cfg.caption_styles()[0]
    fc, label = thumbnail.build_filter(["GOLF BALL", "DIMPLES"], style, "font=Sans")
    assert fc.count("drawtext=") == 2
    assert label == "t1"
    assert style["web_primary"] in fc
    assert "boxblur" in fc and "overlay=(W-w)/2:0" in fc


def test_build_filter_sanitizes_text(cfg):
    style = cfg.caption_styles()[0]
    fc, _ = thumbnail.build_filter(["it's: a TEST!"], style, "font=Sans")
    assert ":text='ITS A TEST!'" in fc  # colon + apostrophe stripped, uppercased


def test_build_filter_no_lines_maps_base(cfg):
    style = cfg.caption_styles()[0]
    fc, label = thumbnail.build_filter([], style, "font=Sans")
    assert label == "base"
    assert "drawtext" not in fc


def test_stage_done_checks_artifact():
    job = Job.create("hidden_things")
    st = ThumbnailStage()
    assert st.done(job) is False
    (job.dir / "thumbnail.jpg").write_bytes(b"x")
    assert st.done(job) is True
