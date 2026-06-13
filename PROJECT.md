# yt-shorts — Project Vision

## Goal
Automate YouTube Shorts production **without** tripping YouTube's 2025
inauthenticity rules — which demonetize templated, mass-produced AI content at the
channel level. The product is not "a script generator"; it is a system that
produces genuine per-video variation and a real point of view, with a thin human
steering layer.

See **[`STRATEGY.md`](STRATEGY.md)** for the full reasoning. The short version:

- **AI is allowed; sameness is not.** One template + swap-the-topic is exactly the
  pattern that gets channels demonetized.
- So originality is **injected at generation** (angle engine, format bank,
  grounding, surface variation) and **enforced at a gate before publish**
  (similarity guard + two batched human gates).
- The system is **niche-agnostic** — niches are config. Default niche is
  *"the hidden ___ of everyday things"* (original by default, deep automation,
  high curiosity-gap retention).

## Architecture at a glance
Each video is a **job** in an idempotent state machine. Stages read/write a shared
job record, so reruns resume failed steps for free.

```
idea → angle engine → [ANGLE GATE] → script (grounded) → similarity guard
     → assets → voice → captions → assemble → metadata → thumbnail
     → [PUBLISH GATE] → upload
```

## Tech stack
- **LLM:** Google Gemini — one model, distinct prompt per stage; web-search
  grounding for factual niches; embeddings for the similarity guard.
- **TTS:** Edge TTS, voice rotated per video.
- **Captions:** Whisper word timing → styled ASS.
- **Assembly:** Remotion (programmatic motion-graphics, default) with an FFmpeg
  fallback — selectable via `RENDER_ENGINE`, isolated behind `AssembleStage`.
- **Upload:** YouTube Data API v3 (resumable, scheduled, dry-run safe).
- **Config:** YAML (niches, lenses, formats, surface).

## The dial
Current setting: automate generation fully; humans gate at **angle + publish**,
both batched. The design goal is the lowest human-touch point that still clears the
originality bar — and to keep that dial in config, not code.

## Future (deliberately deferred)
Dashboard, trend detection, A/B testing, multi-language, thumbnails. None matter
until the pipeline reliably produces videos a human would actually watch.
