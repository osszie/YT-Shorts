"""Transcribe a source video/audio into a word-level transcript.

Reuses the Whisper integration already used for captions, generalised to an
arbitrary media file. Returns duration + words (with timings) + plain text.
"""
from __future__ import annotations

from ..media import captions as caps
from ..media.probe import duration_seconds


def transcribe(media_path: str) -> dict:
    """Return {duration, text, words:[{word,start,end}]} for a media file.

    Raises if no transcript can be produced (e.g. Whisper not installed / no
    speech) — clip mode needs the transcript, so this is a hard requirement
    rather than something to paper over with a fallback.
    """
    total = duration_seconds(media_path)
    timings = caps._whisper_word_timings(media_path)  # [(word, start, end)] or None
    if not timings:
        raise RuntimeError(
            "Transcription unavailable — install openai-whisper and ensure the "
            "source has audible speech.")
    words = [{"word": w, "start": float(s), "end": float(e)} for w, s, e in timings]
    return {
        "duration": total,
        "text": " ".join(w["word"] for w in words),
        "words": words,
    }
