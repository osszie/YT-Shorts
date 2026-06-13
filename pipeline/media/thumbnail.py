"""Branded thumbnail generation (the "thumbnail" box in STRATEGY.md §4's pipeline).

Takes a representative frame from the rendered 9:16 video and composes a 1280x720
thumbnail: the frame centered over a blurred, darkened fill of itself, with a
punchy headline overlaid in the video's caption palette. Pure FFmpeg (already a
dependency) — no Pillow.

`build_filter()` is kept pure so the filter graph can be unit-tested without
running FFmpeg; `render()` degrades to an image-only thumbnail if the text pass
fails (e.g. no usable font), so the stage always yields a usable image.
"""
from __future__ import annotations

import os
import re
import subprocess

WIDTH, HEIGHT = 1280, 720
STOPWORDS = {"the", "a", "an", "of", "on", "in", "why", "how", "that", "this",
             "is", "are", "to", "for", "and", "with", "your", "you"}

_BASE_BG = (f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},boxblur=24:2,eq=brightness=-0.30:saturation=1.10[bg];"
            f"[0:v]scale=-2:{HEIGHT}[fg];[bg][fg]overlay=(W-w)/2:0")


def headline_from_subject(subject: str) -> str:
    """Offline fallback headline: drop filler words, keep the nouns, uppercase."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", subject) if w.lower() not in STOPWORDS]
    return (" ".join(words) or subject).upper().strip()


def wrap(text: str, max_chars: int = 14, max_lines: int = 2) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        cand = (cur + " " + word).strip()
        if not cur or len(cand) <= max_chars:
            cur = cand
        else:
            lines.append(cur)
            cur = word
            if len(lines) == max_lines:
                cur = ""
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines[:max_lines]


def _sanitize(line: str) -> str:
    # Keep only characters that need no FFmpeg drawtext escaping.
    return re.sub(r"[^A-Z0-9 ?!]", "", line.upper()).strip()


def fontspec() -> str:
    env = os.getenv("THUMBNAIL_FONTFILE")
    candidates = [env] if env else []
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return f"fontfile='{path}'"
    return "font=Sans"  # rely on fontconfig's default


def build_filter(lines: list[str], style: dict, font: str, *, fontsize: int = 96) -> tuple[str, str]:
    """Return (filter_complex, output_label). Pure — no FFmpeg invocation."""
    primary = style.get("web_primary", "#FFFF00")
    parts = [f"{_BASE_BG}[base]"]
    label = "base"
    drawable = [ln for ln in (_sanitize(l) for l in lines) if ln]
    n = len(drawable)
    line_h = fontsize + 16
    bottom_margin = 70
    for i, safe in enumerate(drawable):
        y = HEIGHT - bottom_margin - (n - i) * line_h
        out = f"t{i}"
        parts.append(
            f"[{label}]drawtext={font}:text='{safe}':fontsize={fontsize}:"
            f"fontcolor={primary}:borderw=8:bordercolor=black@0.95:"
            f"x=(w-text_w)/2:y={y}[{out}]"
        )
        label = out
    return ";".join(parts), label


def render(video_path: str, out_jpg: str, lines: list[str], style: dict,
           timestamp: float = 1.2) -> tuple[str, bool]:
    """Render the thumbnail. Returns (path, text_rendered)."""
    font = fontspec()
    fc, out_label = build_filter(lines, style, font)
    cmd = ["ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path, "-frames:v", "1",
           "-filter_complex", fc, "-map", f"[{out_label}]", "-q:v", "3", out_jpg]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        return out_jpg, True

    # Degrade to an image-only thumbnail so the stage still produces something.
    cmd2 = ["ffmpeg", "-y", "-ss", str(timestamp), "-i", video_path, "-frames:v", "1",
            "-filter_complex", f"{_BASE_BG}[out]", "-map", "[out]", "-q:v", "3", out_jpg]
    res2 = subprocess.run(cmd2, capture_output=True, text=True)
    if res2.returncode != 0:
        raise RuntimeError(f"thumbnail render failed:\n{res.stderr[-600:]}\n{res2.stderr[-600:]}")
    return out_jpg, False
