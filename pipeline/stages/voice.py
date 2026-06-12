"""Voice stage — TTS the script with the job's rotated voice (Edge TTS)."""
from __future__ import annotations

import asyncio

from ..config import Config
from ..job import Job
from .base import Stage


class VoiceStage(Stage):
    name = "voice"

    def done(self, job: Job) -> bool:
        return job.artifact("voice.mp3").exists()

    def run(self, job: Job, cfg: Config) -> None:
        import edge_tts  # lazy: keep the orchestrator importable without media deps

        voice = job.data["voice"]
        out = job.artifact("voice.mp3")
        out.parent.mkdir(parents=True, exist_ok=True)

        async def _synth():
            communicate = edge_tts.Communicate(
                job.data["script"], voice["edge_voice"],
                rate=voice.get("rate", "+0%"), pitch=voice.get("pitch", "+0Hz"),
            )
            await communicate.save(str(out))

        asyncio.run(_synth())
        job.mark_stage(self.name, f"{voice['edge_voice']} -> voice.mp3")
