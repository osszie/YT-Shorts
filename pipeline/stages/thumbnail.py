"""Thumbnail stage — a branded 1280x720 thumbnail per job, reviewed at the
publish gate alongside the title. Headline comes from the LLM when available
(a 2-4 word curiosity hook), otherwise from the subject. The overlay uses the
video's own caption palette so the thumbnail and video look like one brand.
"""
from __future__ import annotations

from .. import llm
from ..config import Config
from ..job import Job
from ..media import thumbnail
from .base import Stage


class ThumbnailStage(Stage):
    name = "thumbnail"

    def done(self, job: Job) -> bool:
        return job.artifact("thumbnail.jpg").exists()

    def run(self, job: Job, cfg: Config) -> None:
        subject = job.data.get("subject", "")
        angle = job.data.get("angle", "")

        headline = ""
        if llm.available():
            prompt = (
                "Write a thumbnail overlay for a YouTube Short.\n"
                f"Subject: {subject}\nAngle: {angle}\n"
                "2-4 words, ALL CAPS, <= 22 characters total, punchy and "
                "curiosity-driving. No quotes, no punctuation except ? or !.\n"
                'Return JSON: {"headline": "..."}'
            )
            try:
                headline = (llm.generate_json(prompt).get("headline") or "").strip()
            except Exception as e:
                job.log(self.name, f"llm headline failed ({e}); using subject")

        if not headline:
            headline = thumbnail.headline_from_subject(subject)

        lines = thumbnail.wrap(headline)
        ts = max(0.5, float(job.data.get("video_duration", 4.0)) * 0.3)
        _, text_rendered = thumbnail.render(
            str(job.artifact("final.mp4")), str(job.artifact("thumbnail.jpg")),
            lines, job.data["caption_style"], timestamp=ts,
        )
        job.data["thumbnail"] = {
            "headline": headline,
            "lines": lines,
            "text_rendered": text_rendered,
        }
        job.mark_stage(self.name, f"thumbnail.jpg headline='{headline}' text={text_rendered}")
