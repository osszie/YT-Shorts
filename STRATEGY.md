# Strategy & Constraints — Automated YouTube Shorts Channel

Context document for the repo and for Claude Code. **Read this before building or
changing pipeline stages.** It captures *why* the architecture looks the way it
does, not just what to build. The hard constraint driving every decision is
YouTube's monetization policy, not the tech.

## 1. The constraint that shapes everything

YouTube updated its Partner Program rules on **July 15, 2025**, specifically
targeting mass-produced, templated, and faceless AI content. Three facts matter:

- **AI is allowed; sameness is not.** AI tools are fine. The final video must
  carry unique human-added value. Generic, templated output that looks
  mass-produced is what gets demonetized.
- **Enforcement is channel-level.** A few inauthentic videos can demonetize the
  *entire* channel, not just those videos. This is why per-video variety is a
  hard requirement, not a nice-to-have.
- **"Reused content" is separate from copyright.** Reading/reposting material you
  didn't create can be demonetized even with full permission. Permission solves
  copyright; it does nothing for the reused-content rule.

**Design implication:** the thing that makes automation easy (one template, same
voice, same structure, swap the topic) is exactly the thing that gets channels
demonetized. The architecture must produce genuine per-video variation and a real
point of view.

## 2. Originality strategy (the core of the system)

Originality is **injected at generation** and **enforced at a gate before
publish** — two halves. A "make it original" pass bolted onto the end just
produces polished sameness.

### Half 1 — Inject at generation
- **Separate ANGLE from SCRIPT.** First generate the angle — a specific take —
  then write the script to defend that thesis. → `stages/angle.py`, `stages/script.py`
- **Angle engine via rotating "lenses."** Surprise / Hot take / Hidden connection
  / What if / Big meaning. → `config/lenses.yaml`
- **Format bank, not a template.** 6–8 structural skeletons rotated per video.
  → `config/formats.yaml`
- **Ground in real sources.** Pull current, specific facts (web search in the
  pipeline). → `llm.generate_grounded`, used by `stages/script.py`
- **Vary the surface.** Rotate voices, music beds, intro styles, caption
  treatments. → `config/surface.yaml`, `stages/assets.py`

### Half 2 — Enforce at a gate
- **Similarity guard (high value, cheap).** Embed every finished script; store the
  vectors. Above a cosine threshold → reject and regenerate. → `similarity.py`,
  `stages/similarity_guard.py`
- **Two batched human gates.** (1) Angle gate — approve/pick the angle. (2) Publish
  gate — final thumbs-up before upload. Everything between runs untouched.
  → `cli.py` (`angles`/`approve-angle`, `publish-queue`/`approve-publish`)

### The dial
A slider from fully auto → human-steered. Current setting: **automate generation
fully, gate at angle + publish (both batched).**

## 3. Niche decision

Score any niche on four axes: originality-by-default, automation depth, retention
ceiling, saturation. The key tension: the easiest-to-automate niches (Reddit
stories, clip channels) are the most saturated and most demonetization-prone.

| Niche | Born original? | Automatable | Retention | Main risk |
|---|---|---|---|---|
| Original-script explainers | Yes | High | High | Generic execution |
| Streamer clips | No | Med | Med | Reused content + copyright |
| **Reddit stories** | No | High | High | **Hits ALL flags — riskiest** |
| Artist interviews | No | Med | High | Copyright + Content ID |
| Original micro-stories | Yes | High | Depends | Writing quality |

**Recommended:** *"The hidden ___ of everyday things"* — pick one lens
(engineering / economics / psychology / history) and own it. Original by default,
automates deeply, high curiosity-gap retention, saturated only at the generic
level. → shipped as the default niche `config/niches/hidden_things.yaml`.

This repo is **niche-agnostic**: niches are config files. `reddit_stories` is kept
available but is *not* the default, precisely because it hits every flag above.

## 4. Pipeline architecture

Modular, pipeline-based, each stage idempotent. Each video = one job row with a
state machine; each stage is an idempotent function writing to the shared job
record → reruns resume failed steps for free. → `pipeline/job.py`,
`pipeline/orchestrator.py`

```
idea → [angle engine] → ANGLE GATE (human, batched)
     → script (thesis-driven, grounded in real sources)
     → [similarity guard] (auto reject/regen if too similar to catalog)
     → assets (rotated format / voice / style)
     → voice (TTS) → captions (forced-alignment timing)
     → assemble (9:16, fast pacing, branded)
     → metadata (title / description / hashtags)
     → PUBLISH GATE (human, batched) → upload (scheduled)
```

Per-stage tooling here: LLM = Gemini (one model, distinct prompt per stage);
TTS = Edge TTS (per-niche voice rotation); captions = Whisper timing → styled ASS;
assembly = FFmpeg; upload = YouTube Data API v3.

## 5. MVP path

1. **Spine first** — one idea → script → TTS → captions → assemble → export. (Runs
   offline with deterministic fallbacks when no API key is set.)
2. Add the **job/state layer** so reruns work. ✅ `pipeline/job.py`
3. Add **LLM idea/script generation** with the angle split + metadata. ✅
4. Add the **upload API**. ✅
5. **Batching + scheduling last** — trivial once stages are idempotent. ✅ `cli.py new`, `scripts/run_scheduled.sh`

Dashboard, trend detection, A/B testing, multi-language → genuinely future.

## 6. Recurring principle

The easier a format is to fully automate, the riskier it is to monetize. Build for
**automated generation + a thin human steering layer**, not human-absent.

## 7. Control surface — the launcher app (planned)

The "thin human steering layer" deserves a real front door: a desktop application
(working name **Shortcutter**) with a translucent **liquid-glass** UI that lets you pick
the video type, tune settings, and drive the two gates "like opening an app" —
no terminal. It is a *view + controller over this pipeline*, never a replacement:
the originality controls, similarity guard, gates and dry-run-by-default all stay
in the pipeline, so the GUI can't bypass the 2025-policy protections. The dial
(§2) becomes a literal control; the **angle gate** and **publish gate** become the
app's two main review screens.

Full design + technical plan: [`docs/LAUNCHER_DESIGN.md`](docs/LAUNCHER_DESIGN.md).
Status: **design only — no app code yet.**

