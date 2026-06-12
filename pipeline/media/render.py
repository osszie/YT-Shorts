"""FFmpeg assembly: 9:16, branded, fast pacing, burned-in captions.

Carried over from the original render.py. Cover-fits the background to
1080x1920, applies a subtle zoom + drift + a moving progress bar, burns in the
ASS captions, and (when the intro style asks for it) adds a tiny pop+whoosh on
the hook. Background selection rotates across assets/backgrounds/.
"""
from __future__ import annotations

import os
import random
import subprocess

from . import probe
from .. import ROOT

BACKGROUNDS_DIR = ROOT / "assets" / "backgrounds"


def pick_background() -> str:
    if not BACKGROUNDS_DIR.exists():
        raise RuntimeError(f"Backgrounds directory not found: {BACKGROUNDS_DIR}. "
                           "Add .mp4 background videos there.")
    backgrounds = [f for f in os.listdir(BACKGROUNDS_DIR) if f.lower().endswith(".mp4")]
    if not backgrounds:
        raise RuntimeError(f"No .mp4 files in {BACKGROUNDS_DIR}. Add background videos.")
    return str(BACKGROUNDS_DIR / random.choice(backgrounds))


def _start_time(background_path: str, audio_duration: float) -> float:
    bg = probe.duration_seconds(background_path)
    max_start = max(0.0, (bg - audio_duration) if bg > audio_duration else (bg - 1.0))
    return random.uniform(0, max_start) if max_start > 0 else 0.0


def render(background_path: str, voice_mp3: str, captions_ass: str, out_mp4: str,
           duration: float, start_time: float = 0.0, intro_sfx: bool = True) -> str:
    abs_caps = os.path.abspath(captions_ass)
    quoted = "'" + abs_caps.replace("\\", "\\\\").replace(":", "\\:") + "'"
    dur = float(duration)

    base_v = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setpts=PTS-STARTPTS,"
        "scale=iw*1.06:ih*1.06,"
        f"crop=1080:1920:x=(iw-1080)/2:y=(ih-1920)/2 - (ih-1920)*0.05*(t/{dur}),"
        f"subtitles={quoted}"
    )

    if intro_sfx:
        af = (
            "[1:a]volume=1.0[voice];"
            "sine=f=950:d=0.05,afade=t=in:d=0.005,afade=t=out:st=0.03:d=0.02,volume=0.10[pop];"
            "anoisesrc=d=0.22:c=pink:r=44100,highpass=f=500,lowpass=f=7000,"
            "afade=t=in:d=0.02,afade=t=out:st=0.14:d=0.08,volume=0.06[whoosh];"
            "[voice][pop][whoosh]amix=inputs=3:duration=first:dropout_transition=0[aout]"
        )
    else:
        af = "[1:a]volume=1.0[aout]"

    bar_h, bar_thickness = 18, 10
    p = f"min(1\\,t/{dur})"
    bar_graph = (
        f"color=c=black@0.0:s=1080x{bar_h}:d={dur},format=rgba,"
        f"drawbox=x=0:y={(bar_h - bar_thickness) // 2}:w=iw:h={bar_thickness}:color=black@0.35:t=fill:replace=1,"
        f"drawbox=x=0:y={(bar_h - bar_thickness) // 2}:w=iw:h={bar_thickness}:color=lime@0.85:t=fill:replace=1"
    )
    filter_complex = (
        f"[0:v]{base_v}[base];{bar_graph}[bar];"
        f"[base][bar]overlay=x=(W*{p}):y=0:shortest=1[vout];{af}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time), "-stream_loop", "-1", "-i", background_path,
        "-i", voice_mp3,
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-t", str(duration), out_mp4,
    ]
    print(f"  🎬 Rendering {os.path.basename(out_mp4)} ({duration:.1f}s, bg={os.path.basename(background_path)})...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{result.stderr[-1500:]}")
    return out_mp4
