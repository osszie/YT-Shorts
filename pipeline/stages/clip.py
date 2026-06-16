"""Clip-mode SOURCE stages: ingest → transcribe → highlight.

These analyse a long-form source video and propose the best moments. A human
approves them at the clip gate; approved segments fan out into per-clip render
jobs (see cli.py `approve-clip`). The render half (cut + reframe + caption) is a
separate set of stages built on top.
"""
from __future__ import annotations

import json

from ..clip import highlight as hl
from ..clip import transcribe as tr
from ..config import Config
from ..job import Job
from ..media import probe
from .base import Stage


class IngestStage(Stage):
    name = "ingest"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("source", {}).get("duration"))

    def run(self, job: Job, cfg: Config) -> None:
        import os
        from ..clip import download as dl

        path = job.data.get("source_path")
        url = job.data.get("source_url")
        section = job.data.get("source_section")

        if url and not (path and os.path.exists(path)):
            # Fetch a Twitch/YouTube/etc. source (only the section, if given).
            path = dl.download(url, str(job.dir), section=section)
            job.data["source_path"] = path
        elif path and section and not job.data.get("_trimmed"):
            # Local file + a requested window → trim it once with ffmpeg.
            path = self._trim_local(path, section, str(job.artifact("source_trimmed.mp4")))
            job.data["source_path"] = path
            job.data["_trimmed"] = True

        if not path or not os.path.exists(path):
            raise RuntimeError(f"source video not found: {path or url}")
        probe.require("ffprobe")
        duration = probe.duration_seconds(path)
        job.data["source"] = {"path": path, "duration": round(duration, 2),
                              "origin": url or path}
        job.mark_stage(self.name, f"{os.path.basename(path)} ({duration:.0f}s)")

    @staticmethod
    def _trim_local(path: str, section: str, out: str) -> str:
        import subprocess
        start, _, end = section.partition("-")
        probe.require("ffmpeg")
        cmd = ["ffmpeg", "-y", "-ss", start.strip()]
        if end.strip():
            cmd += ["-to", end.strip()]
        cmd += ["-i", path, "-c", "copy", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg trim failed:\n{r.stderr[-400:]}")
        return out


class TranscribeStage(Stage):
    name = "transcribe"

    def done(self, job: Job) -> bool:
        return job.artifact("transcript.json").exists()

    def run(self, job: Job, cfg: Config) -> None:
        transcript = tr.transcribe(job.data["source"]["path"])
        with open(job.artifact("transcript.json"), "w", encoding="utf-8") as f:
            json.dump(transcript, f, ensure_ascii=False)
        job.data["transcript_words"] = len(transcript["words"])
        job.mark_stage(self.name, f"{len(transcript['words'])} words")


class HighlightStage(Stage):
    name = "highlight"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("clips_proposed"))

    def run(self, job: Job, cfg: Config) -> None:
        with open(job.artifact("transcript.json"), "r", encoding="utf-8") as f:
            transcript = json.load(f)
        want = int(job.data.get("want_clips", 3))
        clips = hl.select_highlights(transcript, count=want)
        if not clips:
            raise RuntimeError("no highlight clips could be selected")
        job.data["clips_proposed"] = clips
        job.mark_stage(self.name, f"{len(clips)} clips proposed")
