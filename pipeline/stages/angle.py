"""Angle engine (STRATEGY.md §2, "Half 1 — inject at generation").

The single most important split in the whole system: separate ANGLE from SCRIPT.
We do NOT prompt "write a script about X" (that produces fact-recitation).
Instead we pick a lens + a structural format, generate a specific *take* (the
thesis the script will later defend), and propose a few candidates so the human
ANGLE GATE can approve or pick one. The script stage comes after the gate.
"""
from __future__ import annotations

import random

from .. import llm
from ..config import Config
from ..job import Job
from .base import Stage


class AngleStage(Stage):
    name = "angle"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("angle"))

    def run(self, job: Job, cfg: Config) -> None:
        subject = job.data["subject"]
        domain = job.data.get("lens_domain", "")

        # Rotate the lens + format per video (format bank, not a template).
        lens_id = random.choice(cfg.lens_ids)
        format_id = random.choice(cfg.format_ids)
        lens = cfg.lens(lens_id)
        fmt = cfg.fmt(format_id)

        candidates: list[str] = []
        if llm.available():
            prompt = (
                f"Subject: {subject}\n"
                f"Lens — {lens['name']}: {lens['summary']} {lens['prompt']}\n"
                f"Domain emphasis: {domain}.\n\n"
                "Propose 3 distinct, specific ANGLES (theses) for a ~40s short. Each angle is "
                "ONE punchy sentence stating a particular take the video will argue — not a "
                "topic, not a fact list. They must be genuinely different from each other.\n"
                'Return JSON: {"angles": ["...", "...", "..."]}'
            )
            try:
                out = llm.generate_json(prompt)
                candidates = [a.strip() for a in out.get("angles", []) if a and a.strip()]
            except Exception as e:
                job.log(self.name, f"llm angle failed ({e}); using fallback")

        if not candidates:
            candidates = [
                f"{lens['summary']} — applied to {subject}: {lens['prompt'].strip()}",
                f"What {subject} reveals about {domain} once you actually look.",
            ]

        job.data["lens"] = lens_id
        job.data["format"] = format_id
        job.data["angle_candidates"] = candidates
        job.data["angle"] = candidates[0]          # default pick; human may change it
        job.mark_stage(self.name, f"lens={lens_id} format={format_id}; {len(candidates)} candidates")
