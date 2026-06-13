#!/usr/bin/env python3
"""CI smoke test: exercise a real FFmpeg render end-to-end.

Everything the unit suite stubs (voice/captions/assemble/thumbnail) is run for
real here — except it stays hermetic: no network, no Gemini key, no edge-tts,
no Whisper, no Node/Remotion. We synthesize the background + voice with FFmpeg,
let the captions stage fall back to estimated timings, render with the FFmpeg
engine, and assert a valid final.mp4 + thumbnail.jpg come out the other end.

Run: python scripts/render_smoke.py
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

# Make the repo root importable when run as `python scripts/render_smoke.py`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Force the hermetic path BEFORE importing pipeline modules (assemble reads
# RENDER_ENGINE at import time; llm reads GOOGLE_API_KEY at import time).
os.environ["RENDER_ENGINE"] = "ffmpeg"
os.environ.pop("GOOGLE_API_KEY", None)

from pipeline import ROOT                                    # noqa: E402
from pipeline.config import load_config                     # noqa: E402
from pipeline.job import Job                                 # noqa: E402
from pipeline.media import probe                            # noqa: E402
from pipeline.stages.idea import IdeaStage                  # noqa: E402
from pipeline.stages.angle import AngleStage                # noqa: E402
from pipeline.stages.script import ScriptStage              # noqa: E402
from pipeline.stages.assets import AssetsStage              # noqa: E402
from pipeline.stages.captions import CaptionsStage          # noqa: E402
from pipeline.stages.metadata import MetadataStage          # noqa: E402
from pipeline.stages.assemble import AssembleStage          # noqa: E402
from pipeline.stages.thumbnail import ThumbnailStage        # noqa: E402


def sh(*cmd: str) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("COMMAND FAILED:", " ".join(cmd))
        print(r.stderr[-2000:])
        sys.exit(1)


def main() -> int:
    probe.require("ffmpeg")
    probe.require("ffprobe")

    # 1. Make sure a background video exists (generated, not committed).
    bg_dir = ROOT / "assets" / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)
    bg = bg_dir / "ci_testsrc.mp4"
    if not bg.exists():
        sh("ffmpeg", "-y", "-f", "lavfi",
           "-i", "testsrc=size=720x1280:rate=30:duration=6",
           "-pix_fmt", "yuv420p", str(bg))

    cfg = load_config("hidden_things")
    job = Job.create("hidden_things")

    # 2. Generation (offline fallbacks — no LLM).
    IdeaStage().run(job, cfg)
    AngleStage().run(job, cfg)
    job.approve_gate("angle")
    ScriptStage().run(job, cfg)
    AssetsStage().run(job, cfg)

    # 3. Synthesize voice.mp3 with FFmpeg (stand in for edge-tts; no network).
    sh("ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=5",
       "-c:a", "libmp3lame", "-q:a", "9", str(job.artifact("voice.mp3")))

    # 4. The real render path.
    CaptionsStage().run(job, cfg)     # Whisper absent -> estimated timings
    MetadataStage().run(job, cfg)
    AssembleStage().run(job, cfg)     # real FFmpeg 9:16 render
    ThumbnailStage().run(job, cfg)    # real FFmpeg thumbnail

    final = job.artifact("final.mp4")
    thumb = job.artifact("thumbnail.jpg")

    assert final.exists() and final.stat().st_size > 10_000, "final.mp4 missing or too small"
    assert thumb.exists() and thumb.stat().st_size > 1_000, "thumbnail.jpg missing or too small"
    dur = probe.duration_seconds(str(final))
    assert dur > 1.0, f"final.mp4 unexpectedly short: {dur:.2f}s"

    print("\n✅ render smoke OK")
    print(f"   engine={job.data.get('render_engine')}  "
          f"final.mp4={final.stat().st_size}B  dur={dur:.2f}s  "
          f"thumbnail.jpg={thumb.stat().st_size}B  "
          f"caption_text={'rendered' if job.data.get('thumbnail', {}).get('text_rendered') else 'image-only'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
