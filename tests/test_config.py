import pytest

from pipeline.config import load_config, list_niches


def test_both_niches_load_and_resolve():
    niches = list_niches()
    assert {"hidden_things", "reddit_stories"} <= set(niches)
    for nid in niches:
        cfg = load_config(nid)
        assert cfg.niche_id == nid
        # Every lens/format the niche references must exist in the shared banks.
        for lens_id in cfg.lens_ids:
            assert lens_id in cfg.lenses, f"{nid} references unknown lens {lens_id}"
        for fmt_id in cfg.format_ids:
            assert fmt_id in cfg.formats, f"{nid} references unknown format {fmt_id}"
        # Surface banks resolve to non-empty, niche-filtered lists.
        assert cfg.voices(), f"{nid} has no voices"
        assert cfg.caption_styles(), f"{nid} has no caption styles"
        assert cfg.intro_styles(), f"{nid} has no intro styles"


def test_unknown_niche_raises():
    with pytest.raises(ValueError):
        load_config("does_not_exist")


def test_surface_filtering_is_subset():
    cfg = load_config("reddit_stories")
    all_voice_ids = {v["id"] for v in cfg.surface["voices"]}
    chosen = {v["id"] for v in cfg.voices()}
    assert chosen <= all_voice_ids and chosen
