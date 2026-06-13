# yt-shorts — Project Status

## Overview
Originality-first YouTube Shorts pipeline. Re-architected from the original linear
Reddit-stories scripts into a **niche-agnostic, job-based state machine** that
implements the strategy in [`STRATEGY.md`](STRATEGY.md): inject originality at
generation, enforce it at a gate before publish.

## Architecture

Each video is a **job** (`jobs/<id>/job.json`) advanced by an idempotent
orchestrator through:

```
idea → angle engine → [ANGLE GATE] → script (grounded) → similarity guard
     → assets → voice → captions → assemble → metadata → [PUBLISH GATE] → upload
```

| Component | File | Status |
|---|---|---|
| Job record + state machine | `pipeline/job.py` | ✅ |
| Orchestrator (gates + similarity regen loop) | `pipeline/orchestrator.py` | ✅ |
| Config loader (niche-agnostic) | `pipeline/config.py` | ✅ |
| LLM wrapper (text / JSON / grounded / embed) | `pipeline/llm.py` | ✅ |
| Similarity guard (embeddings + lexical fallback) | `pipeline/similarity.py` | ✅ |
| Idea stage | `pipeline/stages/idea.py` | ✅ |
| Angle engine (lenses, candidates) | `pipeline/stages/angle.py` | ✅ |
| Script (thesis-driven, grounded) | `pipeline/stages/script.py` | ✅ |
| Similarity-guard stage | `pipeline/stages/similarity_guard.py` | ✅ |
| Assets (surface variation) | `pipeline/stages/assets.py` | ✅ |
| Voice (Edge TTS, rotated) | `pipeline/stages/voice.py` | ✅ |
| Captions (Whisper timing → ASS + JSON track) | `pipeline/media/captions.py` | ✅ |
| Assemble (selectable engine) | `pipeline/stages/assemble.py` | ✅ |
| ↳ Remotion engine (default, motion-graphics) | `remotion/`, `pipeline/media/remotion.py` | ✅ |
| ↳ FFmpeg engine (fallback) | `pipeline/media/render.py` | ✅ |
| Metadata (honest SEO) | `pipeline/stages/metadata.py` | ✅ |
| Upload (YouTube API, dry-run safe) | `pipeline/stages/upload.py` + `pipeline/youtube/` | ✅ |
| CLI + two batched gates | `cli.py` | ✅ |
| Niche configs | `config/niches/*.yaml` | ✅ `hidden_things` (default), `reddit_stories` |
| Lenses / formats / surface banks | `config/*.yaml` | ✅ |
| Scheduled batch (to angle gate only) | `scripts/run_scheduled.sh` | ✅ |

## Originality controls (per STRATEGY.md §2)
- **Inject at generation:** angle≠script split, rotating lenses, format bank,
  source grounding, surface variation (voice/captions/intro).
- **Enforce at a gate:** cosine similarity guard with auto-regen; two batched human
  gates (angle, publish).

## Idempotency & resilience
Every stage records its output and a `done()` check, so reruns skip completed work
and resume failed steps. Failures are recorded on the job (`status=failed`,
`error`, `stage`) and fixed by rerunning the same command.

## Graceful degradation
With no `GOOGLE_API_KEY` the pipeline runs the "spine" using deterministic
fallbacks (template idea/angle/script/metadata), the similarity guard falls back to
lexical (Jaccard) comparison, and grounding is skipped. Media stages require FFmpeg
+ Edge TTS + Whisper at runtime.

## Migration notes
The original Reddit-specific scripts (`scripts/agent.py`, `tts.py`, `render.py`,
`captions_bounce.py`, `upload_youtube.py`, `run_all.py`, `scripts/youtube/`) were
replaced. The working, niche-agnostic mechanics (Edge TTS, Whisper captions, FFmpeg
render, YouTube OAuth/upload) were carried over into `pipeline/`. The Reddit niche
remains available as `config/niches/reddit_stories.yaml`, but is **not** the default
because STRATEGY.md flags it as the most demonetization-prone.

## Not yet implemented (deferred by design)
Dashboard, trend detection, A/B testing, thumbnails, multi-language, analytics.
