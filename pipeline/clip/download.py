"""Fetch a source video from a URL (Twitch VOD/clip, YouTube, …) via yt-dlp.

Lets clip mode ingest remote streams, not just local files. yt-dlp supports
Twitch VODs/clips and most sites. `--download-sections` is used when a time
window is given, so a multi-hour VOD only downloads the relevant chunk.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess

_VIDEO_EXTS = ("mp4", "mkv", "webm", "mov", "ts")


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def available() -> bool:
    return shutil.which("yt-dlp") is not None


def download(url: str, out_dir: str, section: str | None = None) -> str:
    """Download `url` into `out_dir`/source.* and return the local path.

    `section` (e.g. "600-1200" or "00:10:00-00:20:00") fetches only that window.
    """
    if not available():
        raise RuntimeError("yt-dlp not installed — needed to fetch URLs / Twitch. "
                           "Install it (pip install yt-dlp).")
    os.makedirs(out_dir, exist_ok=True)
    out_tmpl = os.path.join(out_dir, "source.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "-f", "best[ext=mp4]/bv*+ba/best", "-o", out_tmpl]
    if section:
        # Download only the requested window (efficient for long VODs).
        cmd += ["--download-sections", f"*{section}", "--force-keyframes-at-cuts"]
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed:\n{result.stderr[-600:]}")

    vids = sorted(f for f in glob.glob(os.path.join(out_dir, "source.*"))
                  if f.rsplit(".", 1)[-1].lower() in _VIDEO_EXTS)
    if not vids:
        raise RuntimeError("yt-dlp produced no video file")
    return vids[0]
