# Agent Handoff — yt-shorts

You're picking up a working, well-tested codebase. **Read [`STRATEGY.md`](STRATEGY.md)
first — it's canon** (why the architecture is shaped this way). This file is the
practical orientation + history.

---

## 1. What this project is

An open-source, **originality-first** YouTube Shorts factory, built around YouTube's
2025 anti-"mass-produced-AI" policy. It makes vertical Shorts **two ways** through
one gated engine:

- **Original mode** — *write* a Short from scratch: idea → angle (rotating lenses)
  → script (grounded) → TTS → karaoke captions → render. Has **hooks/angles**
  (the originality engine).
- **Clip mode** — *cut* a Short from existing video (Twitch/YouTube/podcast):
  download → transcribe → AI picks the best moments → **face-tracked 9:16 reframe**
  → karaoke captions → render. **No hooks** — just the moment. (Open-source OpusClip.)

The hard rule from STRATEGY.md: originality is **injected at generation** and
**enforced at human gates before publish**. Don't add a "publish 50 untouched"
path — that's the exact pattern the policy demonetizes.

## 2. How it's built (architecture)

- **Job state machine** (`pipeline/job.py`): each video is a `Job` with a `mode`
  (`original` | `clip_source` | `clip`), a `status`, and a shared `data` dict.
  Jobs live in `jobs/<id>/` (gitignored) with their media artifacts.
- **Orchestrator** (`pipeline/orchestrator.py`): picks a **plan** by mode and runs
  idempotent **stages** in order. Stages have `done()` (skip if already done) so
  reruns resume failed steps. Two human **gates** park jobs:
  - Original plan: idea → angle → **[ANGLE GATE]** → script → similarity_guard →
    assets → voice → captions → assemble → metadata → thumbnail → **[PUBLISH GATE]** → upload
  - Clip source plan: ingest → transcribe → highlight → **[CLIP GATE]** (fan-out)
  - Clip render plan: assets → cut_reframe → captions → assemble → metadata →
    thumbnail → **[PUBLISH GATE]** → upload
- **Stages** live in `pipeline/stages/`. Clip-specific: `stages/clip.py` (source
  analysis) and `stages/clip_render.py` (render).
- **Clip logic** in `pipeline/clip/`: `download.py` (yt-dlp), `transcribe.py`
  (Whisper), `highlight.py` (LLM picks moments), `reframe.py` (OpenCV face track +
  ffmpeg cut/crop).
- **LLM is model-agnostic** (`pipeline/llm.py` facade + `pipeline/providers/`):
  `LLM_PROVIDER=gemini` (default) or `ollama` (fully local). The facade owns
  pacing + retry/backoff so every backend + stage shares them.
- **Two render engines** (`pipeline/media/`): **Remotion** (`remotion/` project,
  default — animated word-by-word karaoke captions) and **FFmpeg** fallback.
  Selected by `RENDER_ENGINE`. Both modes use them.
- **Config is data, not code** (`config/`): `niches/*.yaml`, `lenses.yaml`,
  `formats.yaml`, `surface.yaml` (voices/caption styles/intro styles).
- **CLI** (`cli.py`): the entrypoint and the two gates. See §4.

## 3. Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit: GOOGLE_API_KEY (or LLM_PROVIDER=ollama)
cd remotion && npm install && cd ..   # for the Remotion render engine
python cli.py doctor          # tells you exactly what's missing
python cli.py doctor --probe  # also makes one live LLM call to check the key/quota
```
Runtime deps that must be present locally (the cloud sandbox lacked them, all have
fallbacks, `doctor` flags each): **FFmpeg**, **Node 18+** (Remotion), **Edge-TTS**
(voice), **Whisper** (transcription), **OpenCV** (face tracking), **yt-dlp** (URL/
Twitch ingest). Put `.mp4` backgrounds in `assets/backgrounds/` for original mode.
For real uploads, drop OAuth `credentials.json` in the repo root.

## 4. The two workflows

**Original (write):**
```
python cli.py new --count 5            # idea+angle, park at ANGLE gate
python cli.py angles                   # review
python cli.py approve-angle <id> --pick 2     # or --edit "..."  / --all
python cli.py run --all                # script → … → thumbnail, park at PUBLISH gate
python cli.py publish-queue
python cli.py approve-publish <id>      # upload (dry-run unless YOUTUBE_DRY_RUN=false)
```

**Clip (cut existing video):**
```
python cli.py clip <local.mp4 OR https://twitch.tv/videos/... > --section 00:30:00-00:50:00 --count 5
python cli.py clips                    # review AI-picked moments (CLIP gate)
python cli.py approve-clip <id> --pick 1,3      # fan out to clip render jobs
python cli.py run --all                # cut + face-track 9:16 + captions
python cli.py publish-queue → approve-publish <id>
```
Other: `status`, `show <id>`, `niches`, `reject <id>`, `doctor`.

## 5. Conventions / guardrails (don't break these)

- **STRATEGY.md is canon.** New niches are YAML in `config/niches/` — no code.
- **Two gates stay.** Uploads are **dry-run by default** (`YOUTUBE_DRY_RUN`).
- **Clips have NO hook** (hooks/angles are original-mode only). Clip titles are
  plain/descriptive; `CLIP_TITLE_MODE=auto|blank`; clip thumbnails are a clean frame.
- **Fail loud, not garbage:** when the LLM is *configured but failing*, the
  angle/script stages re-raise (job → failed/retryable) instead of emitting
  scaffolding-leaking templates. Deterministic fallbacks run only in true offline
  (no key) mode.
- **Tests are offline & fast** (`tests/`, currently ~85). They mock ffmpeg/whisper/
  opencv/yt-dlp/LLM so they run in CI with only PyYAML+python-dotenv+pytest. Keep it
  that way; gate real-binary tests behind `shutil.which(...)` skips. Two CI
  workflows: `ci.yml` (unit) + `render-smoke.yml` (a real FFmpeg render).
- Run `python -m pytest -q` and (if touching Remotion) `cd remotion && npx tsc --noEmit`
  before committing.

## 6. Git / PR state (as of this handoff)

- Default/base branch: **`switch-to-hf`**. Work branch:
  **`claude/plan-implementation-strategy-tudmoq`**.
- **Merged into `switch-to-hf`:** the whole pipeline + both modes up to and
  including clip mode (Twitch ingest → AI clips → face-AWARE 9:16 → Remotion
  karaoke, no hook). PRs #3–#12.
- **Open PR #13** (not yet merged): **dynamic per-frame face tracking** (smooth
  follow) + the **clip review gate** mockup + **mobile-friendly** mockups. If
  you're working locally on the latest branch you already have these commits; if
  on `switch-to-hf`, merge PR #13 first.

## 7. UI (designed, not built)

**Shortcutter** — a Mac-first, liquid-glass desktop launcher over this pipeline.
Design + mockups only: `docs/LAUNCHER_DESIGN.md`, `docs/CLIP_MODE_DESIGN.md`,
`docs/launcher-mockup.html` (Create screen), `docs/clip-gate-mockup.html` (clip
gate). Mockups are mobile-responsive. Planned stack: React + Tauri shell + a small
FastAPI bridge over the existing pipeline (never re-implement pipeline logic in the UI).

## 8. Good next steps

1. **Run it for real** — produce one real Short and clip one real Twitch VOD end to
   end (the sandbox couldn't: no TTS/Whisper/OpenCV/Twitch/upload there).
2. **Build Shortcutter Phase 1** — read-only glass shell over `jobs/`.
3. **Clip polish** — multi-speaker/split-screen layouts, B-roll, "Write or Clip" home screen.
4. Deferred per strategy: analytics, trend detection, A/B testing.

## 9. Map (where things are)

```
cli.py                     entrypoint + gates
config/                    niches + lenses + formats + surface (all behaviour)
pipeline/
  job.py orchestrator.py   state machine + plans/gates
  llm.py  providers/       model-agnostic LLM (gemini/ollama) + retry/pacing
  similarity.py  doctor.py
  stages/                  original stages + clip.py + clip_render.py
  clip/                    download / transcribe / highlight / reframe
  media/                   captions (whisper→ASS+JSON) · render (ffmpeg) · remotion · thumbnail · probe
  youtube/                 OAuth + resumable upload
remotion/                  Remotion project (Short + Clip compositions)
tests/                     ~85 offline tests
docs/                      STRATEGY context + launcher/clip design + mockups
scripts/render_smoke.py    real-render CI smoke
STRATEGY.md                READ FIRST
```
