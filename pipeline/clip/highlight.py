"""Highlight selection — the LLM reads the transcript and picks the best moments.

This is clip mode's "secret sauce" and the model-agnostic analog of the angle
engine: given a timestamped transcript, return self-contained segments to cut
into Shorts. Long transcripts are CHUNKED — the model sees the whole video, not
just the opening minutes — candidates are merged, overlap-deduped and ranked.
Offline (no model) it falls back to evenly-spaced windows so the spine works.
"""
from __future__ import annotations

import os

from .. import llm

TARGET_LEN = 40.0
# Per-LLM-call transcript budget. Kept modest so it also fits small local models
# (Ollama); Gemini could take far more. A 2h VOD ≈ 100k chars ≈ 6-7 chunks.
CHUNK_CHARS = int(os.getenv("HIGHLIGHT_CHUNK_CHARS", "16000"))
MAX_CHUNKS = int(os.getenv("HIGHLIGHT_MAX_CHUNKS", "12"))
# Two candidates overlap if the intersection covers more than this fraction of
# the shorter one; the lower-scored duplicate is dropped.
OVERLAP_FRAC = 0.5


def _timestamped_lines(words: list[dict]) -> list[str]:
    """The transcript as compact timestamped sentence-ish lines (untruncated)."""
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
    return lines


def _transcript_chunks(words: list[dict], max_chars: int) -> list[str]:
    """Group the timestamped lines into chunks of <= max_chars each."""
    chunks, cur, size = [], [], 0
    for ln in _timestamped_lines(words):
        if cur and size + len(ln) + 1 > max_chars:
            chunks.append("\n".join(cur))
            cur, size = [], 0
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


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
            "title": (c.get("title") or c.get("hook") or "").strip() or "Highlight",
            "reason": (c.get("reason") or "").strip(),
            "score": float(c.get("score", 0.5)) if str(c.get("score", "")).strip() else 0.5,
        })
    out.sort(key=lambda c: c["score"], reverse=True)
    return out


def _overlap_frac(a: dict, b: dict) -> float:
    inter = min(a["end"], b["end"]) - max(a["start"], b["start"])
    if inter <= 0:
        return 0.0
    shorter = min(a["end"] - a["start"], b["end"] - b["start"])
    return inter / max(shorter, 0.001)


def _dedupe_overlaps(clips: list[dict]) -> list[dict]:
    """Drop candidates that substantially overlap a higher-scored one.
    Expects `clips` sorted by score (desc), as _sanitize returns them."""
    kept: list[dict] = []
    for c in clips:
        if all(_overlap_frac(c, k) < OVERLAP_FRAC for k in kept):
            kept.append(c)
    return kept


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
                          "title": f"Clip {i + 1}", "reason": "evenly-spaced (offline)", "score": 0.5})
    return clips


def _chunk_prompt(chunk_text: str, idx: int, total: int, duration: float,
                  count: int, min_len: float, max_len: float) -> str:
    part = f" This is part {idx + 1} of {total} of the transcript." if total > 1 else ""
    return (
        "You are selecting the best short-form clips from a long video's transcript.\n"
        f"The full video is {duration:.0f}s long.{part} Timestamps are in seconds:\n\n"
        f"{chunk_text}\n\n"
        f"Pick up to {count} of the BEST self-contained moments in THIS part to cut into "
        f"vertical Shorts. Each must stand alone and be {int(min_len)}-{int(max_len)}s long. "
        "Prefer surprising, funny, insightful, or emotionally strong moments; return fewer "
        "(or none) if this part has no strong moment.\n"
        "Give each a short, plain, descriptive title of what the moment is about "
        "(for the upload) — not clickbait.\n"
        'Return JSON: {"clips": [{"start": <sec>, "end": <sec>, "title": "what it\'s about", '
        '"reason": "why it works", "score": 0..1}]}'
    )


def select_highlights(transcript: dict, count: int = 3,
                      min_len: float = 18.0, max_len: float = 60.0) -> list[dict]:
    """Return up to `count` clip segments [{start,end,title,reason,score}].

    Clips are existing moments, not generated content — so this picks segments
    and gives them a plain descriptive title (NOT a hook; hooks/angles belong to
    original from-scratch videos only, STRATEGY §2 vs §8). The whole transcript
    is analysed in chunks so long VODs are covered end to end.
    """
    duration = transcript["duration"]
    words = transcript.get("words", [])

    if llm.available() and words:
        chunks = _transcript_chunks(words, CHUNK_CHARS)
        if len(chunks) > MAX_CHUNKS:
            # No silent caps: say exactly what part of the video goes unanalysed.
            print(f"  ⚠️  transcript needs {len(chunks)} chunks; analysing the first "
                  f"{MAX_CHUNKS} (~{MAX_CHUNKS / len(chunks):.0%} of the video). "
                  f"Raise HIGHLIGHT_MAX_CHUNKS to cover more.")
            chunks = chunks[:MAX_CHUNKS]
        candidates: list[dict] = []
        for i, chunk_text in enumerate(chunks):
            out = llm.generate_json(  # rate-limit errors propagate to the stage
                _chunk_prompt(chunk_text, i, len(chunks), duration, count, min_len, max_len))
            candidates.extend(out.get("clips", []))
        clips = _dedupe_overlaps(_sanitize(candidates, duration, min_len, max_len))
        if len(chunks) > 1:
            print(f"  🔎 analysed {len(chunks)} transcript chunks → "
                  f"{len(candidates)} candidates → {len(clips)} distinct")
        if clips:
            return clips[:count]

    return _evenly_spaced(duration, count)[:count]
