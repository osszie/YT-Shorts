import pytest

from pipeline.job import Job
from pipeline.stages.idea import IdeaStage
from pipeline.stages.angle import AngleStage
from pipeline.stages.script import ScriptStage
from pipeline.stages.similarity_guard import SimilarityGuardStage
from pipeline.stages.assets import AssetsStage
from pipeline.stages.metadata import MetadataStage
from pipeline.stages.base import SimilarityTooHigh


def _job():
    return Job.create("hidden_things")


def test_idea_sets_subject_and_domain(cfg):
    job = _job()
    IdeaStage().run(job, cfg)
    assert job.data["subject"]
    assert job.data["lens_domain"] in cfg.niche["idea"]["lens_domains"]
    assert IdeaStage().done(job)


def test_idea_avoids_recent_subjects_offline(cfg):
    seeds = cfg.niche["idea"]["seeds"]
    # Use up every seed but one across prior jobs; idea must pick the survivor.
    survivor = seeds[0]
    for s in seeds[1:]:
        j = Job.create("hidden_things"); j.data["subject"] = s; j.save()
    job = _job()
    IdeaStage().run(job, cfg)
    assert job.data["subject"] == survivor


def test_angle_sets_lens_format_and_candidates(cfg):
    job = _job(); IdeaStage().run(job, cfg)
    AngleStage().run(job, cfg)
    assert job.data["lens"] in cfg.lens_ids
    assert job.data["format"] in cfg.format_ids
    assert job.data["angle_candidates"]
    assert job.data["angle"] == job.data["angle_candidates"][0]


def test_script_fallback_has_words(cfg):
    job = _job(); IdeaStage().run(job, cfg); AngleStage().run(job, cfg)
    ScriptStage().run(job, cfg)
    assert job.data["script_words"] > 0
    assert job.data["subject"] in job.data["script"]


def test_script_fallback_varies_by_attempt(cfg):
    job = _job(); IdeaStage().run(job, cfg); AngleStage().run(job, cfg)
    s0 = ScriptStage._fallback("golf ball dimples", "they reduce drag", {}, 0)
    s1 = ScriptStage._fallback("golf ball dimples", "they reduce drag", {}, 1)
    assert s0 != s1


def test_similarity_guard_passes_then_rejects_duplicate(cfg):
    job = _job(); IdeaStage().run(job, cfg); AngleStage().run(job, cfg); ScriptStage().run(job, cfg)
    SimilarityGuardStage().run(job, cfg)
    assert job.data["similarity"]["passed"] is True

    dup = _job()
    dup.data.update(subject=job.data["subject"], angle=job.data["angle"],
                    format=job.data["format"], script=job.data["script"])
    with pytest.raises(SimilarityTooHigh):
        SimilarityGuardStage().run(dup, cfg)


def test_assets_picks_within_niche_surface(cfg):
    job = _job()
    AssetsStage().run(job, cfg)
    assert job.data["voice"]["id"] in {v["id"] for v in cfg.voices()}
    assert job.data["caption_style"]["id"] in {s["id"] for s in cfg.caption_styles()}
    assert job.data["intro_style"]["id"] in {i["id"] for i in cfg.intro_styles()}


def test_metadata_builds_title_and_tags(cfg):
    job = _job(); IdeaStage().run(job, cfg); AngleStage().run(job, cfg)
    MetadataStage().run(job, cfg)
    meta = job.data["metadata"]
    assert meta["title"] and len(meta["title"]) <= 100
    assert meta["tags"]
    assert "#shorts" in meta["description"]


# --- free-tier optimizations ---------------------------------------------

def test_generate_subjects_offline_distinct(cfg):
    from pipeline.stages.idea import generate_subjects
    out = generate_subjects(cfg, 3)
    assert len(out) == 3
    for subj, dom in out:
        assert isinstance(subj, str) and subj
        assert dom in cfg.niche["idea"]["lens_domains"]


def test_generate_subjects_bulk_llm_single_call(cfg, monkeypatch):
    import pipeline.stages.idea as idea
    calls = {"n": 0}

    def fake_json(*_a, **_k):
        calls["n"] += 1
        return {"subjects": ["A thing", "B thing", "C thing"]}

    monkeypatch.setattr(idea.llm, "available", lambda: True)
    monkeypatch.setattr(idea.llm, "generate_json", fake_json)
    out = idea.generate_subjects(cfg, 3)
    assert [s for s, _ in out] == ["A thing", "B thing", "C thing"]
    assert calls["n"] == 1  # one call for the whole batch


def test_thumbnail_headline_defaults_to_subject(cfg, monkeypatch):
    import pipeline.stages.thumbnail as th
    from pipeline.media import thumbnail as tmod
    monkeypatch.setattr(th.llm, "available", lambda: True)   # available...
    monkeypatch.delenv("THUMBNAIL_LLM_HEADLINE", raising=False)  # ...but not enabled
    monkeypatch.setattr(tmod, "render", lambda *a, **k: ("out.jpg", True))  # no ffmpeg
    job = Job.create("hidden_things")
    job.data.update(subject="the dimples on a golf ball", angle="x",
                    caption_style=cfg.caption_styles()[0], video_duration=5.0)
    th.ThumbnailStage().run(job, cfg)
    assert job.data["thumbnail"]["headline"] == tmod.headline_from_subject("the dimples on a golf ball")
