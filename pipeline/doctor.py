"""Environment preflight (`python cli.py doctor`).

Getting the first watchable Short out of the pipe (STRATEGY.md §5) is gated by
environment, not code: FFmpeg, Node/Remotion, a Gemini key, OAuth credentials and
background videos all have to be in place. This reports what's ready vs. missing
so that's obvious before a batch is run, instead of discovering it when a stage
fails mid-pipeline.

Checks are dependency-light: presence is detected via importlib/shutil, never by
importing the heavy libraries themselves.
"""
from __future__ import annotations

import importlib.util
import os
import shutil

from . import ROOT
from .config import list_niches, load_config

OK, WARN, FAIL = "ok", "warn", "fail"  # FAIL = hard blocker for producing a video


def _have(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _check_config() -> list[tuple[str, str, str]]:
    out = []
    for nid in list_niches():
        try:
            load_config(nid)
            out.append((f"niche:{nid}", OK, "loads"))
        except Exception as e:  # noqa: BLE001
            out.append((f"niche:{nid}", FAIL, str(e)))
    return out


def _pkg(label: str, module: str, hint: str, *, required: bool) -> tuple[str, str, str]:
    if _have(module):
        return (label, OK, "present")
    return (label, FAIL if required else WARN, hint)


def _check_python() -> list[tuple[str, str, str]]:
    return [
        _pkg("PyYAML", "yaml", "pip install -r requirements.txt", required=True),
        _pkg("edge-tts (voice)", "edge_tts", "pip install -r requirements.txt", required=True),
        _pkg("whisper (caption timing)", "whisper",
             "optional — falls back to estimated timings", required=False),
        _pkg("google-generativeai (LLM)", "google.generativeai",
             "optional — pipeline runs with deterministic fallbacks", required=False),
        _pkg("google-api-python-client (upload)", "googleapiclient",
             "needed only for real uploads", required=False),
    ]


def _check_binaries() -> list[tuple[str, str, str]]:
    return [(b, OK, "present") if shutil.which(b) else (b, FAIL, "install FFmpeg")
            for b in ("ffmpeg", "ffprobe")]


def _check_render_engine() -> list[tuple[str, str, str]]:
    engine = os.getenv("RENDER_ENGINE", "remotion").lower()
    if engine != "remotion":
        return [("render engine = ffmpeg", OK, "filter-graph renderer")]
    node_ok = bool(shutil.which("node") and shutil.which("npx"))
    deps_ok = (ROOT / "remotion" / "node_modules" / "remotion").exists()
    if node_ok and deps_ok:
        return [("remotion render engine", OK, "Node + deps present")]
    return [("remotion render engine", WARN,
             "Node/deps missing — will fall back to ffmpeg. Run: (cd remotion && npm install)")]


def _check_clip() -> list[tuple[str, str, str]]:
    yt = shutil.which("yt-dlp")
    return [
        ("yt-dlp (URL / Twitch ingest)", OK if yt else WARN,
         "present" if yt else "pip install yt-dlp — needed only to clip URLs (Twitch/YouTube)"),
        ("opencv (face-aware reframing)", OK if _have("cv2") else WARN,
         "present" if _have("cv2") else "pip install opencv-python-headless — without it clips center-crop"),
    ]


def _check_backgrounds() -> list[tuple[str, str, str]]:
    d = ROOT / "assets" / "backgrounds"
    n = len(list(d.glob("*.mp4"))) if d.exists() else 0
    return [("background videos", OK if n else FAIL,
             f"{n} in assets/backgrounds/" if n else "add .mp4 files to assets/backgrounds/")]


def _check_llm() -> list[tuple[str, str, str]]:
    key = bool(os.getenv("GOOGLE_API_KEY"))
    return [("GOOGLE_API_KEY", OK if key else WARN,
             "set (note: free-tier requests-per-minute is low — use a paid tier for batches)"
             if key else "unset — LLM angles/scripts/grounding/embeddings disabled (fallbacks used)")]


def probe_llm() -> tuple[str, str, str]:
    """Live one-shot Gemini call (retries disabled) to check the key actually
    works *right now* — distinguishing a valid-but-rate-limited key from a
    rejected one or a network/proxy problem. Never returns FAIL: even a bad key
    only limits LLM features; the offline spine still makes videos."""
    if not os.getenv("GOOGLE_API_KEY"):
        return ("Gemini live probe", WARN, "no GOOGLE_API_KEY — skipped (offline fallbacks used)")
    if not _have("google.generativeai"):
        return ("Gemini live probe", WARN, "google-generativeai not installed")
    from . import llm
    saved = llm.MAX_RETRIES
    llm.MAX_RETRIES = 0  # don't let backoff hang the probe on a hard rate limit
    try:
        txt = llm.generate_text("Reply with the single word: ok", max_tokens=8)
        return ("Gemini live probe", OK, f"reachable, quota available ({llm.MODEL_NAME})")
    except Exception as e:  # noqa: BLE001
        s = str(e).lower()
        if any(t in s for t in ("429", "quota", "exhausted", "rate")):
            return ("Gemini live probe", WARN,
                    "rate-limited / out of quota — wait, or use a paid tier for batches")
        if any(t in s for t in ("api key", "api_key", "permission", "401", "403", "invalid", "denied")):
            return ("Gemini live probe", WARN, "key rejected — check GOOGLE_API_KEY (offline spine still works)")
        if any(t in s for t in ("certificate", "ssl", "connect", "handshake")):
            return ("Gemini live probe", WARN, "can't reach Gemini (network/proxy) — try GEMINI_TRANSPORT=rest")
        return ("Gemini live probe", WARN, f"call failed: {str(e)[:80]}")
    finally:
        llm.MAX_RETRIES = saved


def _check_upload() -> list[tuple[str, str, str]]:
    dry = os.getenv("YOUTUBE_DRY_RUN", "true").lower() == "true"
    creds = (ROOT / os.getenv("YOUTUBE_CLIENT_SECRETS", "credentials.json")).exists()
    return [
        ("YOUTUBE_DRY_RUN", OK, "true (safe — nothing publishes)" if dry else "false (WILL PUBLISH)"),
        ("credentials.json", OK if creds else WARN, "present" if creds else "needed only for real uploads"),
    ]


def run_checks(probe: bool = False) -> dict[str, list[tuple[str, str, str]]]:
    groups = {
        "Config": _check_config(),
        "Python packages": _check_python(),
        "Binaries": _check_binaries(),
        "Render engine": _check_render_engine(),
        "Backgrounds": _check_backgrounds(),
        "Clip mode": _check_clip(),
        "LLM": _check_llm(),
        "Upload": _check_upload(),
    }
    if probe:
        groups["LLM"] = groups["LLM"] + [probe_llm()]
    return groups


def summarize(groups: dict[str, list[tuple[str, str, str]]]) -> dict:
    flat = [c for checks in groups.values() for c in checks]
    fails = [name for name, status, _ in flat if status == FAIL]
    warns = [name for name, status, _ in flat if status == WARN]
    # "Spine ready" = can generate + assemble a video (dry-run upload). Every FAIL
    # is a spine blocker; WARNs only limit optional features (LLM, real upload).
    return {"ready": not fails, "fails": fails, "warns": warns}
