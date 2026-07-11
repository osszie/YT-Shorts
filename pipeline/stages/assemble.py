"""Assemble stage — burn the video. Selectable render engine (Remotion default,
FFmpeg fallback), chosen by RENDER_ENGINE. The engine is isolated here so it can
change without touching any other stage.
"""
from __future__ import annotations

import json
import os

from ..config import Config
from ..job import Job
from ..media import probe, render, remotion
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
        intro_sfx = bool(job.data.get("intro_style", {}).get("sfx", True))
        out_mp4 = str(job.artifact("final.mp4"))
        # Read at run time (not import time) so .env load order can't stale it —
        # matches how the clip render stage selects its engine.
        engine = os.getenv("RENDER_ENGINE", "remotion").lower()

        if engine == "remotion":
            if remotion.available():
                try:
                    self._render_remotion(job, voice_mp3, background, duration, intro_sfx, out_mp4)
                    job.data["render_engine"] = "remotion"
                except remotion.RemotionUnavailable as e:
                    job.log(self.name, f"remotion unavailable ({e}); falling back to ffmpeg")
                    engine = "ffmpeg"
            else:
                job.log(self.name, "remotion not installed; falling back to ffmpeg")
                engine = "ffmpeg"

        if engine != "remotion":
            self._render_ffmpeg(background, voice_mp3, job, duration, intro_sfx, out_mp4)
            job.data["render_engine"] = "ffmpeg"

        job.data["video_duration"] = round(duration, 2)
        job.mark_stage(self.name, f"final.mp4 ({duration:.1f}s, engine={job.data['render_engine']})")

    def _render_remotion(self, job, voice_mp3, background, duration, intro_sfx, out_mp4):
        with open(job.artifact("captions.json"), "r", encoding="utf-8") as f:
            track = json.load(f)["chunks"]
        meta = job.data.get("metadata", {})
        title = meta.get("title") or job.data.get("subject", "")
        remotion.render(
            job_dir=job.dir, voice_mp3=voice_mp3, background_path=background,
            caption_track=track, duration=duration, style=job.data["caption_style"],
            title=title, intro_sfx=intro_sfx, out_mp4=out_mp4,
        )

    def _render_ffmpeg(self, background, voice_mp3, job, duration, intro_sfx, out_mp4):
        start = render._start_time(background, duration)
        render.render(
            background_path=background, voice_mp3=voice_mp3,
            captions_ass=str(job.artifact("captions.ass")), out_mp4=out_mp4,
            duration=duration, start_time=start, intro_sfx=intro_sfx,
        )
