"""Highlight selection — the LLM reads the transcript and picks the best moments.

This is clip mode's "secret sauce" and the model-agnostic analog of the angle
engine: given a timestamped transcript, return self-contained, hooky segments to
cut into Shorts. Offline (no model) it falls back to evenly-spaced windows so the
spine still works.
"""
from __future__ import annotations

import json

from .. import llm

TARGET_LEN = 40.0


def _timestamped_lines(words: list[dict], max_chars: int = 6000) -> str:
    """Compact, timestamped transcript for the prompt (sentence-ish chunks)."""
    lines, cur, start = [], [], None
    for w in words:
        if start is None:
            start = w["start"]
        cur.append(w["word"])
        if w["word"].endswith((".", "!", "?")) or len(cur) >= 18:
            lines.append(f"[{start:.0f}s] " + " ".join(cur))
            cur, start = [], None
    if cur:
        lines.append(f"[{start:.0f}s] " + " ".join(cur))
    text = "\n".join(lines)
    return text[:max_chars]


def _sanitize(raw: list[dict], duration: float, min_len: float, max_len: float) -> list[dict]:
    out = []
    for c in raw:
        try:
            start = max(0.0, float(c.get("start", 0)))
            end = min(duration, float(c.get("end", 0)))
        except (TypeError, ValueError):
            continue
        if end - start < min_len:
            end = min(duration, start + min_len)
        if end - start > max_len:
            end = start + max_len
        if end <= start or start >= duration:
            continue
        out.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "hook": (c.get("hook") or "").strip() or "Highlight",
            "reason": (c.get("reason") or "").strip(),
            "score": float(c.get("score", 0.5)) if str(c.get("score", "")).strip() else 0.5,
        })
    out.sort(key=lambda c: c["score"], reverse=True)
    return out


def _evenly_spaced(duration: float, count: int, target: float = TARGET_LEN) -> list[dict]:
    clips = []
    if duration <= 0:
        return clips
    n = max(1, min(count, int(duration // target) or 1))
    step = duration / n
    for i in range(n):
        start = i * step
        end = min(duration, start + min(target, step))
        if end - start >= 5:
            clips.append({"start": round(start, 2), "end": round(end, 2),
                          "hook": f"Clip {i + 1}", "reason": "evenly-spaced (offline)", "score": 0.5})
    return clips


def select_highlights(transcript: dict, count: int = 3,
                      min_len: float = 18.0, max_len: float = 60.0) -> list[dict]:
    """Return up to `count` clip segments [{start,end,hook,reason,score}]."""
    duration = transcript["duration"]
    words = transcript.get("words", [])

    if llm.available() and words:
        prompt = (
            "You are selecting the best short-form clips from a long video's transcript.\n"
            f"The video is {duration:.0f}s long. Timestamps are in seconds:\n\n"
            f"{_timestamped_lines(words)}\n\n"
            f"Pick the {count} BEST self-contained moments to cut into vertical Shorts. "
            f"Each must stand alone, open with a hook, and be {int(min_len)}-{int(max_len)}s long. "
            "Prefer surprising, funny, insightful, or emotionally strong moments.\n"
            'Return JSON: {"clips": [{"start": <sec>, "end": <sec>, "hook": "punchy title", '
            '"reason": "why it works", "score": 0..1}]}'
        )
        out = llm.generate_json(prompt)  # rate-limit errors propagate to the stage
        clips = _sanitize(out.get("clips", []), duration, min_len, max_len)
        if clips:
            return clips[:count]

    return _evenly_spaced(duration, count)[:count]
