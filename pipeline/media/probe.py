"""Small ffprobe/ffmpeg helpers shared by the media stages."""
from __future__ import annotations

import subprocess


def require(tool: str) -> None:
    try:
        subprocess.run([tool, "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError(f"{tool} not found. Install FFmpeg (brew install ffmpeg / apt install ffmpeg).")


def duration_seconds(media_path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(media_path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def dimensions(media_path: str) -> tuple[int, int]:
    """Return (width, height) of the first video stream."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(media_path)],
        capture_output=True, text=True, check=True,
    )
    w, h = out.stdout.strip().split("\n")[0].split("x")[:2]
    return int(w), int(h)
