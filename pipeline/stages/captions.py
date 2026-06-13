"""Captions stage — Whisper-timed track, written as both ASS (FFmpeg) and JSON
(Remotion) so either render engine can consume it."""
from __future__ import annotations

import json

from ..config import Config
from ..job import Job
from ..media import captions
from .base import Stage


class CaptionsStage(Stage):
    name = "captions"

    def done(self, job: Job) -> bool:
        # Both artifacts are required: the JSON feeds Remotion, the ASS feeds the
        # FFmpeg engine. Requiring both keeps the rerun/resume flow correct if a
        # run is interrupted between writing them.
        return job.artifact("captions.json").exists() and job.artifact("captions.ass").exists()

    def run(self, job: Job, cfg: Config) -> None:
        script = job.data["script"]
        voice_mp3 = str(job.artifact("voice.mp3"))

        # Engine-neutral timing track (computed once: audio is transcribed once).
        track, total = captions.build_track(script, voice_mp3)
        with open(job.artifact("captions.json"), "w", encoding="utf-8") as f:
            json.dump({"duration": total, "chunks": track}, f, ensure_ascii=False)

        # ASS file for the FFmpeg engine, written from the same track (no re-transcribe).
        captions.write_ass(track, str(job.artifact("captions.ass")), job.data["caption_style"])

        job.data["caption_chunks"] = len(track)
        job.mark_stage(self.name, f"{len(track)} chunks ({job.data['caption_style']['id']})")
