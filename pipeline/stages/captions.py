"""Captions stage — Whisper-timed ASS captions in the job's caption style."""
from __future__ import annotations

from ..config import Config
from ..job import Job
from ..media import captions
from .base import Stage


class CaptionsStage(Stage):
    name = "captions"

    def done(self, job: Job) -> bool:
        return job.artifact("captions.ass").exists()

    def run(self, job: Job, cfg: Config) -> None:
        captions.generate(
            script_text=job.data["script"],
            voice_mp3=str(job.artifact("voice.mp3")),
            out_ass=str(job.artifact("captions.ass")),
            style=job.data["caption_style"],
        )
        job.mark_stage(self.name, f"captions.ass ({job.data['caption_style']['id']})")
