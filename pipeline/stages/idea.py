"""Idea stage — produce one concrete subject + a lens-domain to view it through.

Deliberately small: the *originality* comes from the angle engine next, not
here. With an LLM key we generate a fresh, specific subject in the niche's
spirit (and steer clear of recent subjects); offline we draw from the seed pool.
"""
from __future__ import annotations

import random

from .. import llm
from ..config import Config
from ..job import Job, recent_subjects
from .base import Stage


class IdeaStage(Stage):
    name = "idea"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("subject"))

    def run(self, job: Job, cfg: Config) -> None:
        idea_cfg = cfg.niche.get("idea", {})
        seeds = idea_cfg.get("seeds", [])
        domains = idea_cfg.get("lens_domains", ["engineering"])
        domain = random.choice(domains)

        # Cross-job memory: what the channel has already covered, so we don't
        # repeat subjects video-to-video.
        recent = recent_subjects(exclude_job_id=job.id)
        recent_lower = {s.lower() for s in recent}

        subject = None
        if llm.available():
            prompt = (
                f"You are sourcing one idea for the YouTube niche: {cfg.niche['name']}.\n"
                f"{cfg.niche.get('description', '')}\n\n"
                f"Give ONE specific, concrete subject whose hidden {domain} story would "
                f"genuinely surprise a smart viewer. Be physical and precise (an object or "
                f"detail), never generic 'random facts'. Examples of the right altitude: "
                f"{', '.join(seeds[:6])}.\n"
                f"Avoid anything close to these already-covered subjects: "
                f"{', '.join(recent[:30]) if recent else '(none yet)'}.\n"
                'Return JSON: {"subject": "..."}'
            )
            try:
                subject = (llm.generate_json(prompt).get("subject") or "").strip()
            except Exception as e:
                job.log(self.name, f"llm idea failed ({e}); using seed")

        # Offline / fallback: prefer a seed the channel hasn't used yet.
        if not subject:
            unused = [s for s in seeds if s.lower() not in recent_lower]
            pool = unused or seeds
            subject = random.choice(pool) if pool else "an everyday object"

        job.data["subject"] = subject
        job.data["lens_domain"] = domain
        job.data["recent_subjects_seen"] = len(recent)
        job.mark_stage(self.name, f"subject='{subject}' domain={domain} (avoided {len(recent)} prior)")
