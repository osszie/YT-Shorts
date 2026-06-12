"""Assets stage — surface variation (STRATEGY.md §2, "Vary the surface").

Rotate voice, caption treatment and intro style across the small set the niche
opts into. Identical voice+music+motion is an automation fingerprint even when
scripts differ, so each job locks in its own surface here before media render.
"""
from __future__ import annotations

import random

from ..config import Config
from ..job import Job
from .base import Stage


class AssetsStage(Stage):
    name = "assets"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("voice"))

    def run(self, job: Job, cfg: Config) -> None:
        voice = random.choice(cfg.voices())
        caption_style = random.choice(cfg.caption_styles())
        intro_style = random.choice(cfg.intro_styles())

        job.data["voice"] = voice
        job.data["caption_style"] = caption_style
        job.data["intro_style"] = intro_style
        job.mark_stage(self.name,
                       f"voice={voice['id']} captions={caption_style['id']} intro={intro_style['id']}")
