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
