"""Assemble stage — burn captions over a rotated background into a 9:16 MP4."""
from __future__ import annotations

from ..config import Config
from ..job import Job
from ..media import probe, render
from .base import Stage


class AssembleStage(Stage):
    name = "assemble"

    def done(self, job: Job) -> bool:
        return job.artifact("final.mp4").exists()

    def run(self, job: Job, cfg: Config) -> None:
        probe.require("ffmpeg")
        probe.require("ffprobe")

        voice_mp3 = str(job.artifact("voice.mp3"))
        duration = probe.duration_seconds(voice_mp3)
        background = render.pick_background()
        start = render._start_time(background, duration)
        intro_sfx = bool(job.data.get("intro_style", {}).get("sfx", True))

        render.render(
            background_path=background,
            voice_mp3=voice_mp3,
            captions_ass=str(job.artifact("captions.ass")),
            out_mp4=str(job.artifact("final.mp4")),
            duration=duration,
            start_time=start,
            intro_sfx=intro_sfx,
        )
        job.data["video_duration"] = round(duration, 2)
        job.mark_stage(self.name, f"final.mp4 ({duration:.1f}s)")
