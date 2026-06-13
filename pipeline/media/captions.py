"""Whisper-timed, phrase-chunked ASS captions (CapCut style), parameterized by a
surface caption style so videos vary their look.

Carried over from the original captions_bounce.py but simplified to centered
phrase chunks (\\an5) — more robust than the old per-word X/Y grid — while
keeping the bounce animation, hook emphasis and keyword highlight.
"""
from __future__ import annotations

import math
import re
import ssl

from .probe import duration_seconds

# Whisper downloads its model over HTTPS; some environments have broken certs.
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

CENTER_Y = 900
HOOK_WINDOW_SECONDS = 2.0
MIN_ONSCREEN = 0.12


def _floor_cs(t: float) -> float:
    return math.floor(t * 100.0) / 100.0


def _ceil_cs(t: float) -> float:
    return math.ceil(t * 100.0) / 100.0


def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _whisper_word_timings(audio_path: str):
    if not WHISPER_AVAILABLE:
        return None
    try:
        model = whisper.load_model("medium")
        result = model.transcribe(audio_path, word_timestamps=True, language="en",
                                  initial_prompt=None, fp16=False)
        timings = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                word = (w.get("word") or "").strip()
                if word:
                    timings.append((word, float(w.get("start", 0)), float(w.get("end", 0))))
        return timings or None
    except Exception as e:
        print(f"  ⚠️  Whisper failed ({e}); falling back to estimated timings.")
        return None


def _estimated_word_timings(script_text: str, total: float):
    words = re.findall(r"\S+", script_text)
    if not words:
        return []
    per = total / len(words)
    out, t = [], 0.0
    for w in words:
        out.append((w, t, t + per))
        t += per
    return out


def _sanitize(timings, total):
    out, prev_end = [], 0.0
    for word, start, end in timings:
        s = max(0.0, min(start, total))
        e = max(0.0, min(end, total))
        if s < prev_end:
            s = prev_end
        if e < s:
            e = s
        if (e - s) < MIN_ONSCREEN:
            e = min(total, s + MIN_ONSCREEN)
        sq, eq = _floor_cs(s), _ceil_cs(e)
        if eq <= sq:
            eq = min(total, sq + 0.01)
        out.append((word, sq, eq))
        prev_end = eq
    if out:
        w, s, _ = out[-1]
        out[-1] = (w, s, _ceil_cs(total))
    return out


def _chunk(timings, max_words=6, min_sec=0.9, max_sec=2.2):
    chunks, cur, start = [], [], None
    for word, s, e in timings:
        if start is None:
            start = s
        cur.append((word, s, e))
        dur = e - start
        finalize = len(cur) >= max_words or (dur + 0.3) > max_sec
        if word.endswith((".", "!", "?", ",", ";", ":")) and dur >= min_sec:
            finalize = True
        if finalize:
            chunks.append((" ".join(w for w, _, _ in cur), start, e))
            cur, start = [], None
    if cur:
        chunks.append((" ".join(w for w, _, _ in cur), start, timings[-1][2]))
    return chunks


def _bounce() -> str:
    return ("{\\fscx80\\fscy80\\be2"
            "\\t(0,120,\\fscx112\\fscy112\\be5)"
            "\\t(120,220,\\fscx100\\fscy100\\be3)}")


def _emphasis(text: str, start: float, highlight: str) -> str:
    tags = []
    if start <= HOOK_WINDOW_SECONDS:
        tags.append("\\bord10\\shad6\\be6\\fscx125\\fscy125")
    first = (text.split() or [""])[0]
    clean = re.sub(r"[^\w']+", "", first).strip()
    if clean.isupper() and len(clean) >= 3:
        tags.append(f"\\1c{highlight}")
    return "{" + "".join(tags) + "}" if tags else ""


def build_track(script_text: str, voice_mp3: str) -> tuple[list[dict], float]:
    """Engine-neutral caption track: phrase chunks + audio duration.

    Returns ([{"text", "start", "end"} ...], total_seconds). Shared by both the
    FFmpeg (ASS) and Remotion (React) renderers so timing is computed once.
    """
    total = duration_seconds(voice_mp3)
    timings = _whisper_word_timings(voice_mp3) or _estimated_word_timings(script_text, total)
    timings = _sanitize(timings, total)
    chunks = [{"text": t, "start": s, "end": e} for t, s, e in _chunk(timings)]
    return chunks, total


def generate(script_text: str, voice_mp3: str, out_ass: str, style: dict) -> str:
    """Write an ASS caption file for `voice_mp3`, styled per `style`."""
    track, _ = build_track(script_text, voice_mp3)
    chunks = [(c["text"], c["start"], c["end"]) for c in track]

    fontname = style.get("fontname", "Arial")
    fontsize = int(style.get("fontsize", 72))
    primary = style.get("primary", "&H0000FFFF&")
    outline = style.get("outline", "&H00000000&")
    highlight = style.get("highlight", "&H0000A5FF&")

    with open(out_ass, "w", encoding="utf-8") as f:
        f.write("[Script Info]\n")
        f.write("ScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n")
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
                "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
                "MarginL, MarginR, MarginV, Encoding\n")
        f.write(f"Style: Default,{fontname},{fontsize},{primary},{primary},{outline},"
                "&H00000000&,1,0,0,0,100,100,0,0,0,8,4,5,10,10,10,1\n\n")
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for text, start, end in chunks:
            pos = f"{{\\pos(540,{CENTER_Y})}}"
            tags = f"{pos}{_emphasis(text, start, highlight)}{_bounce()}"
            f.write(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{tags}{text}\n")
    return out_ass
