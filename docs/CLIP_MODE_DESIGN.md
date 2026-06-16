# Clip Mode — Repurpose existing video into Shorts (Design + Strategy)

> Status: **design only.** No build yet. This describes a second *source mode* for
> the pipeline in [`STRATEGY.md`](../STRATEGY.md): keep everything we have
> (generate original Shorts) **and** add the ability to cut long-form video
> (podcasts, streams, talks) into auto-captioned 9:16 Shorts — an open-source,
> model-agnostic "OpusClip".

---

## 1. Vision: two ways to make a Short

The project becomes a Shorts **factory with two source modes**, sharing one engine:

- **ORIGINAL** (today): idea → angle → script → TTS → captions → render.
  *We write a Short.*
- **CLIP** (new): ingest a long video → transcribe → auto-find the best moments →
  cut → reframe to 9:16 → caption → render. *We cut a Short out of existing video.*

Better than OpusClip because it's **open-source and model-agnostic** — pick Gemini,
a local Ollama model, whatever — and it reuses our gated, originality-aware
pipeline instead of a black box.

## 2. Why it fits what we already have

Clip mode is mostly **reuse**, not rebuild. It rides the same rails:

| Already built | Reused by clip mode? |
|---|---|
| Job state machine + idempotent orchestrator | ✅ same |
| Two batched human gates | ✅ angle gate → **clip-selection gate**; publish gate identical |
| Whisper word-level captions | ✅ **this is exactly clip mode's transcription** |
| Assemble (Remotion/FFmpeg) + modern karaoke captions | ✅ burn captions on the reframed clip |
| Metadata, thumbnail, upload | ✅ same |
| Niche-agnostic YAML config + `doctor` | ✅ same patterns |

The **angle engine** (LLM injects a *take*) and the new **highlight engine** (LLM
injects *which moment*) are siblings — both are "use the model to add a point of
view," which is the whole philosophy of STRATEGY.md §2.

## 3. Policy caveat (read this)

STRATEGY.md §1: the 2025 "reused content" rule can demonetize reposting material
you didn't create. **Clip mode is for YOUR OWN long-form content** (your podcast,
your stream, your talk) or content you're licensed to use. Clipping other people's
videos is exactly the risk the policy targets. The UI/docs must make this explicit
and default to "this is my content."

## 4. Architecture — a `mode` branch in the pipeline

Each job gets `mode: "original" | "clip"`. The orchestrator picks a stage **plan**
by mode. One long video fans out into many clip jobs.

```
ORIGINAL plan (unchanged):
  idea → angle → [ANGLE GATE] → script → similarity_guard
       → assets → voice → captions → assemble → metadata → thumbnail
       → [PUBLISH GATE] → upload

CLIP — Source job (one per input video):
  ingest → transcribe → highlight → [CLIP GATE]
                                       │  (human approves which moments)
                                       ▼  fan-out: one clip job per approved segment
CLIP — Clip job (one per Short):
  cut+reframe → captions(from transcript slice) → assemble
              → metadata → thumbnail → [PUBLISH GATE] → upload
```

The clip gate is the angle gate's analog: instead of "pick the take," you "pick the
moments." The publish gate is identical (preview the 9:16 clip + caption + title).

## 5. New components (the only real new code)

- **`ingest`** — accept a local video file (MVP); later a URL via `yt-dlp`. Probe
  duration/streams, copy/reference into the source job.
- **`transcribe`** — Whisper the whole source → word-level transcript with
  timestamps. We already do this for captions; generalize it to transcribe an
  arbitrary file and return segments + words.
- **`highlight`** (the "secret sauce") — the LLM reads the timestamped transcript
  and returns the best self-contained moments: `{start, end, hook, reason, score}`.
  20–60s, strong opening line, complete thought. Model-agnostic — this is the
  open-source edge. Long transcripts are chunked to fit context.
- **`cut+reframe`** — FFmpeg trims `[start,end]` and reframes 16:9 → 9:16. MVP:
  center-crop (or configurable anchor). Phase 2: active-speaker / face-tracked
  crop so the talking head stays in frame.
- **Fan-out** — one source job → N clip jobs (a new one-to-many in the job model;
  clip jobs carry `{source_path, start, end, transcript_slice, hook}`).

## 6. Reframing 16:9 → 9:16 (the part that makes it look pro)

- **MVP:** center crop, or a config anchor (`center` / `left` / `right`). Fine for
  centered single-speaker podcasts.
- **Phase 2:** detect the active speaker / face (OpenCV or MediaPipe) and crop to
  follow them; smooth the motion so it doesn't jitter.
- **Later:** layouts — full-frame, "headcam on top + captions below," split-screen
  for two speakers, optional B-roll. All just Remotion compositions.

Captions reuse our existing **karaoke** style, timed from the source transcript
slice — so clipped Shorts look identical in caption polish to generated ones.

## 7. Model-agnostic ("whatever AI you choose")

To deliver the "open-source, any model" promise, generalize the LLM layer into a
**provider abstraction** (`pipeline/llm.py` → a small interface) with backends:

- **Gemini** (current default),
- **Ollama** (fully local / open — the project actually started on Ollama),
- optionally OpenAI-compatible endpoints.

Selected via `LLM_PROVIDER` env. This benefits **both** modes (original + clip) and
makes the whole project genuinely model-agnostic. Worth doing alongside clip mode.

## 8. Config

A clip "profile" (YAML, same spirit as niches): target clip length range, max clips
per source, reframe mode/anchor, min highlight score, caption style. Niche-agnostic
design is unchanged; clip profiles just live next to niches.

## 9. CLI (mirrors the original flow)

```
cli.py clip <video.mp4> [--count N] [--min-score 0.6]   # ingest→transcribe→highlight, park at clip gate
cli.py clips                                             # review proposed moments (gate 1)
cli.py approve-clip <source_id> [--pick 1,3,5]           # fan out approved segments to clip jobs
cli.py run --all                                         # cut/reframe/caption/metadata, park at publish gate
cli.py publish-queue / approve-publish                  # identical to today
```

## 10. Phasing (build order, later)

0. **Design** ✅ (this doc).
1. **Clip MVP** — local file → transcribe → LLM highlights → clip gate → center-crop
   cut + burn karaoke captions → one Short. *Fully buildable & testable in the
   cloud sandbox (FFmpeg + Whisper + a sample video).*
2. **Fan-out** to multiple clips + per-clip metadata/thumbnail.
3. **Face/active-speaker reframing.**
4. **URL ingest (`yt-dlp`)**, layouts, B-roll.
5. **LLM provider abstraction** (Ollama/local) — can slot in earlier; benefits both modes.

## 11. Risks

- **Reused-content policy** — own/licensed content only (see §3).
- **Reframing quality** — naive crops cut faces off; why §6 Phase 2 matters.
- **Transcript length / cost** — chunk the transcript for highlight selection.
- **Processing time** — long videos take real CPU (transcription + encoding).
- **Scope creep** — keep the original mode first-class; clip mode is additive.

## 12. Decisions

- **Reframing:** **face / active-speaker tracking from day one** (OpenCV/MediaPipe)
  so the talking head stays in frame — not just a center crop.
- **Ingest:** local files **and** URLs — Twitch VODs/clips, YouTube, etc. via
  `yt-dlp`, with an optional `--section start-end` to fetch only a window of a
  long VOD (so multi-hour Twitch streams don't download in full).
- **Model provider:** **build the provider abstraction now** (Gemini + local Ollama)
  so "any model" is real from the start — benefits original mode too.

Launcher: the clip-selection gate is mocked in
[`docs/clip-gate-mockup.html`](clip-gate-mockup.html) (paste a Twitch/YouTube
source → review AI-picked moments → approve which to render). Open later: the
"Write or Clip" home screen.

---

*Additive by design: original mode stays exactly as-is; clip mode is a second
front door into the same gated engine.*
