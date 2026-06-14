"""Remotion render engine (programmatic motion-graphics, STRATEGY.md §4 "best
long-term").

Drives the Remotion project in ./remotion via its CLI. We compute the caption
track + timing in Python (shared with the FFmpeg path), stage the job's assets
into a per-job public dir, and pass everything else as input props. This keeps
the React composition pure and deterministic.

Requires Node 18+ and `npm install` inside ./remotion. The first render also
downloads a headless Chrome shell. If any of that is missing, AssembleStage
falls back to the FFmpeg engine.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess

from .. import ROOT

REMOTION_DIR = ROOT / "remotion"
FPS = int(os.getenv("REMOTION_FPS", "30"))
COMPOSITION_ID = "Short"


class RemotionUnavailable(RuntimeError):
    pass


def available() -> bool:
    return (REMOTION_DIR / "node_modules" / "remotion").exists() and shutil.which("npx") is not None


def _check() -> None:
    if shutil.which("node") is None or shutil.which("npx") is None:
        raise RemotionUnavailable("Node.js / npx not found (need Node 18+).")
    if not (REMOTION_DIR / "node_modules").exists():
        raise RemotionUnavailable(f"Remotion deps not installed. Run: (cd {REMOTION_DIR} && npm install)")


def render(*, job_dir, voice_mp3: str, background_path: str, caption_track: list[dict],
           duration: float, style: dict, title: str, intro_sfx: bool, out_mp4: str) -> str:
    """Render the job with Remotion. `job_dir` becomes the public dir."""
    _check()
    job_dir = str(job_dir)

    # Stage the background into the job (public) dir so staticFile() can serve it.
    staged_bg = os.path.join(job_dir, "background.mp4")
    if os.path.abspath(background_path) != os.path.abspath(staged_bg):
        shutil.copyfile(background_path, staged_bg)

    duration_in_frames = max(1, math.ceil(duration * FPS))
    bg_duration_in_frames = max(1, math.ceil(_safe_duration(staged_bg) * FPS))

    props = {
        "audioSrc": "voice.mp3",
        "backgroundSrc": "background.mp4",
        "captions": caption_track,
        "title": title,
        "introSfx": bool(intro_sfx),
        "fps": FPS,
        "durationInFrames": duration_in_frames,
        "bgDurationInFrames": bg_duration_in_frames,
        "style": {
            "primary": style.get("web_primary", "#FFFF00"),
            "highlight": style.get("web_highlight", "#FFA500"),
            "fontFamily": style.get("fontname", "Arial"),
            "fontSize": int(style.get("fontsize", 72)),
        },
    }
    props_path = os.path.join(job_dir, "remotion.props.json")
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f)

    cmd = [
        "npx", "remotion", "render", "src/index.ts", COMPOSITION_ID,
        os.path.abspath(out_mp4),
        f"--props={os.path.abspath(props_path)}",
        f"--public-dir={os.path.abspath(job_dir)}",
        f"--frames=0-{duration_in_frames - 1}",
        "--log=error",
    ]
    # Use an existing Chromium instead of downloading Remotion's headless shell.
    # Lets renders work on hosts whose egress blocks remotion.media (sandboxes,
    # locked-down CI). Override with REMOTION_BROWSER_EXECUTABLE.
    browser = _browser_executable()
    if browser:
        cmd.append(f"--browser-executable={browser}")
    # Chrome mode: "headless-shell" (Remotion default) needs the downloadable
    # shell; "chrome-for-testing" uses the new headless mode that a normal/system
    # Chrome supports. When we supply our own binary it's a full Chrome, so
    # default to chrome-for-testing unless overridden.
    chrome_mode = os.getenv("REMOTION_CHROME_MODE") or ("chrome-for-testing" if browser else None)
    if chrome_mode:
        cmd.append(f"--chrome-mode={chrome_mode}")
    print(f"  🎬 Remotion rendering {os.path.basename(out_mp4)} ({duration:.1f}s @ {FPS}fps)"
          + (f" [chromium={os.path.basename(browser)}, mode={chrome_mode}]" if browser else "") + "...")
    result = subprocess.run(cmd, cwd=str(REMOTION_DIR), capture_output=True, text=True)
    if result.returncode != 0:
        raise RemotionUnavailable(f"Remotion render failed:\n{result.stderr[-1500:]}")
    return out_mp4


def _browser_executable() -> str | None:
    """Path to a Chromium/Chrome to render with, or None to let Remotion manage
    its own headless shell (the default on a normal network).

    Only honours an explicit REMOTION_BROWSER_EXECUTABLE — useful on hosts whose
    egress blocks Remotion's shell download, where you can point it at a
    compatible chrome-headless-shell. We deliberately do NOT auto-discover a
    system/Playwright Chrome: forcing an arbitrary binary can break the common
    case (e.g. a full Chrome that dropped old-headless mode).
    """
    explicit = os.getenv("REMOTION_BROWSER_EXECUTABLE")
    return explicit if explicit and os.path.exists(explicit) else None


def _safe_duration(path: str) -> float:
    from .probe import duration_seconds
    try:
        return duration_seconds(path)
    except Exception:
        return 1.0
