# yt-shorts

An **originality-first** pipeline for automated YouTube Shorts. It is built around
one hard constraint: YouTube's 2025 Partner Program rules demonetize
mass-produced, templated, faceless AI content *at the channel level*. So this repo
does the opposite of "one template, swap the topic" — it injects originality at
generation and enforces it at a gate before publish.

> Read [`STRATEGY.md`](STRATEGY.md) first. It explains *why* the architecture
> looks the way it does. This README is the *how*.

## What it does

Every video is a **job** moving through an idempotent state machine, steered by a
human at exactly **two batched gates**:

```
idea → angle engine → [ANGLE GATE] → script (grounded) → similarity guard
     → assets (rotated voice/captions/intro) → voice → captions → assemble
     → metadata → thumbnail → [PUBLISH GATE] → upload
```

The originality layer:
- **Angle engine** — separates the *angle* (a specific take, via rotating lenses)
  from the *script*, so videos argue a thesis instead of reciting facts.
- **Format bank** — 6–8 structural skeletons rotated per video.
- **Source grounding** — factual niches pull real, current facts via web search.
- **Surface variation** — voices, caption treatments and intro styles rotate.
- **Similarity guard** — embeds every finished script and rejects/regenerates
  anything too close to the back catalog.
- **Two human gates** — approve the angle, approve the publish. Everything
  between runs untouched.

It is **niche-agnostic**: niches are config files. The default is
`hidden_things` ("the hidden ___ of everyday things"); `reddit_stories` ships too
but is *not* recommended (see STRATEGY.md §3).

## Prerequisites

- Python 3.9+
- `FFmpeg` (`brew install ffmpeg` / `apt install ffmpeg`) — for TTS probing and the FFmpeg render fallback
- **Node 18+** (optional) — for the default Remotion render engine; without it the pipeline renders with FFmpeg
- A Google **Gemini** API key (optional but recommended) — angles, scripts,
  grounding, metadata and the similarity embeddings. Without it the pipeline
  still runs the "spine" using deterministic fallbacks.
- A Google Cloud project with **YouTube Data API v3** (only for real uploads).

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env
```

Add background videos as `.mp4` into `assets/backgrounds/` (looped + center-cropped
to 1080×1920). For uploads, drop OAuth `credentials.json` (Desktop app) in the repo
root; first real upload opens a browser to authorize.

For the default **Remotion** render engine, install its deps once:

```bash
cd remotion && npm install && cd ..
```

The first render downloads a headless Chrome shell. If Node/Remotion isn't present,
the pipeline automatically renders with FFmpeg instead.

## Usage — the weekly loop

```bash
# 0. Preflight: what's ready vs. missing (FFmpeg, Remotion, key, backgrounds…).
python cli.py doctor

# 1. Fill the queue: create jobs and auto-run them to the ANGLE gate.
python cli.py new --count 20

# 2. Gate 1 (batched): review proposed angles, then approve/pick.
python cli.py angles
python cli.py approve-angle <job_id> --pick 2     # or --edit "my own angle"
python cli.py approve-angle --all                 # batch-approve defaults

# 3. Run automated stages (script → … → metadata), parking at the PUBLISH gate.
python cli.py run --all

# 4. Gate 2 (batched): review finished videos.
python cli.py publish-queue

# 5. Approve + upload (dry-run unless YOUTUBE_DRY_RUN=false).
python cli.py approve-publish <job_id>
```

Other commands: `python cli.py status` (overview), `show <id>` (full job record),
`niches`, `reject <id>`. Run `python cli.py --help`.

### Where things live (per job)

Each job is a directory under `jobs/<job_id>/` (gitignored):
- `job.json` — the shared state record every stage reads/writes
- `voice.mp3`, `captions.ass`/`captions.json`, `final.mp4`, `thumbnail.jpg` — media artifacts

Because every stage records its output and checks for it, **reruns resume failed
steps** without restarting: fix the cause, run the same command again.

## Configuration

All content behaviour is config, not code:

| File | Purpose |
|---|---|
| `config/niches/<id>.yaml` | A niche: topic source, which lenses/formats/voices it uses, target length, grounding, metadata |
| `config/lenses.yaml` | The angle lenses (Surprise / Hot take / Hidden connection / What if / Big meaning) |
| `config/formats.yaml` | The structural format bank |
| `config/surface.yaml` | Voices, caption styles, intro styles to rotate |

Key `.env` settings (see `.env.example`): `NICHE`, `GOOGLE_API_KEY`,
`GEMINI_MODEL`, `SIMILARITY_THRESHOLD`, `YOUTUBE_DRY_RUN`,
`YOUTUBE_PRIVACY_STATUS`, `SCHEDULE_HOURS`.

To add a niche, drop a new `config/niches/<id>.yaml` and run
`python cli.py new --niche <id>`. No code changes.

### Render engines

Assembly is isolated behind `AssembleStage`, so the engine is swappable via
`RENDER_ENGINE`:

- **`remotion`** (default) — programmatic React/motion-graphics (`remotion/`):
  animated captions, zoom/drift background, progress bar, subject header. Best for
  the "hidden things" explainer look; this is where animated diagrams/callouts
  belong as the channel matures. Needs Node + `npm install` in `remotion/`.
- **`ffmpeg`** — the original filter-graph renderer (`pipeline/media/render.py`).
  Zero Node dependency; used automatically when Remotion isn't available.

Caption *timing* is computed once (Whisper → `captions.json`) and shared by both
engines, so they stay in sync. Iterate on the visuals live with
`cd remotion && npm run studio`.

## Scheduling

`scripts/run_scheduled.sh` generates a daily batch **to the angle gate only** — it
never auto-uploads, because that would bypass the human gates the policy requires.
See `scheduling/` for the macOS `launchd` setup.

## Project structure

```
yt-shorts/
├── cli.py                  # entrypoint: jobs, the two gates, status
├── config/                 # niches + lenses + formats + surface (all behaviour)
├── pipeline/
│   ├── job.py              # job record + state machine
│   ├── orchestrator.py     # runs stages in order, gates, similarity regen
│   ├── config.py  llm.py  similarity.py
│   ├── stages/             # idea, angle, script, similarity_guard, assets,
│   │                       #   voice, captions, assemble, metadata, upload
│   ├── media/              # whisper captions + ffmpeg/remotion render engines
│   └── youtube/            # OAuth + resumable upload
├── remotion/               # Remotion project (default render engine)
├── assets/backgrounds/     # your .mp4 backgrounds (gitignored)
├── jobs/  catalog/         # per-job state + similarity catalog (gitignored)
└── STRATEGY.md             # why the architecture is shaped this way — read first
```

## Notes

- Nothing publishes by accident: `YOUTUBE_DRY_RUN=true` by default.
- No Gemini key? The spine still runs with deterministic fallbacks (offline),
  the similarity guard falls back to lexical comparison, grounding is skipped.
- `jobs/`, `catalog/`, `output/`, `.env` and credentials are all gitignored.
