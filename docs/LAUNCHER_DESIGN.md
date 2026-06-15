# Shortcutter — Launcher & Control Surface (Design + Strategy)

> **Shortcutter** — it turns Shorts production into a shortcut: open the app, pick
> a type, steer at two gates, done. (Shorts + shortcut.)

Status: **design only.** No app code yet. This document is the plan for a **Mac-first**
desktop application that becomes the control surface for the pipeline described in
[`STRATEGY.md`](../STRATEGY.md). Read that first — Shortcutter is a *front end* over
that system, never a replacement for its guardrails.

---

## 1. Vision

Open Shortcutter like a native Mac app. A calm, translucent "liquid glass"
workspace where you:

- pick **what kind of video** to make (the niche / video type),
- tune the **settings** you care about (voice, caption style, length, how many,
  how hands-off),
- approve **angles** and **publishes** at the two batched gates,
- watch jobs move through the pipeline and **preview** the finished Shorts,

…without ever touching a terminal. The CLI keeps working underneath for power use
and automation; Shortcutter is the friendly steering wheel.

## 2. Why a launcher fits the strategy (not just polish)

The strategy already prescribes **"the dial": automate generation fully, gate at
angle + publish (both batched)** (STRATEGY.md §2). That is *exactly* an app:

- The **dial** → a literal control in the UI (fully-auto ↔ human-steered).
- The **angle gate** → a review screen of candidate angles you approve/pick/edit.
- The **publish gate** → a review screen with the rendered video + metadata you
  green-light.
- **Everything between** runs untouched, shown as a live queue.

So the launcher doesn't bolt new behaviour on — it *surfaces* the behaviour the
pipeline was built around. The "significant human input" the 2025 policy wants
becomes two pleasant clicks per video instead of CLI commands.

## 3. Information architecture (screens)

A left **glass rail** with these destinations; the main area is a layered glass
canvas over a slow-moving gradient.

| Screen | Purpose | Maps to |
|---|---|---|
| **Home** | At-a-glance: counts by state, recent Shorts, health. | `cli.py status` + `doctor` |
| **Create** | Choose video type + settings, set batch size, **Generate**. | `cli.py new` |
| **Angles** | Gate #1 — approve / pick / edit / reject proposed angles (batched). | `angles` / `approve-angle` |
| **Queue** | Live pipeline: each job's stage, similarity score, errors, retries. | the job state machine |
| **Publish** | Gate #2 — preview video + thumbnail + metadata, approve → upload. | `publish-queue` / `approve-publish` |
| **Library** | Past videos: uploaded / scheduled / draft, links, (later) analytics. | upload records |
| **Settings** | Keys, default niche, render engine, model, paths, the dial. | `.env` + `config/*` |

The two **gates** (Angles, Publish) are the emotional center of the app — they're
where the human actually steers, so they get the most design love (see §5).

## 4. Create screen — "what kind of video + what settings"

This is the screen the request is really about. It's a visual editor over the
existing niche-agnostic config, so nothing here is bespoke — every control reads
from / writes to config the pipeline already understands.

**Pick a video type** (cards, one per niche in `config/niches/`):
- *The Hidden ___ of Everyday Things* (default)
- *Original first-person stories*
- *(any niche you add as YAML shows up here automatically)*

**Settings — curated by default, Advanced on demand.** Most batches need only a
handful of choices, so the Create screen shows a **curated** set and tucks the rest
behind an **"Advanced ⌄"** disclosure (collapsed by default). Curation is purely
about *what's surfaced first* — every control still reads/writes config the
pipeline already understands.

*Curated (always visible):*
- **How many** — batch size slider (1–25).
- **The dial** — *Fully auto* ↔ *Review angles* ↔ *Review everything* (sets which
  gates pause).
- **Voice** — pick one, or "Rotate" → `config/surface.yaml`.
- **Caption style** — live preview swatches (the white-text + accent-box look) →
  `config/surface.yaml`.
- **Publishing** — privacy + the **dry-run toggle (on by default**, with a clear
  warning when turned off).

*Advanced (hidden behind "Advanced ⌄"):*
- **Lens emphasis** — favour certain angle lenses → `config/lenses.yaml`.
- **Format mix** — which skeletons to rotate → `config/formats.yaml`.
- **Render engine** — Remotion / FFmpeg / Auto → `RENDER_ENGINE`.
- **Length & pacing** — target seconds → niche `script.target_words`.
- **Grounding** — real facts on/off → niche `script.grounding`.
- **Model** — Gemini model picker → `GEMINI_MODEL`.
- **Similarity threshold**, **schedule**, **paths & API keys**.

A primary **Generate** button (softly glowing) kicks off a batch and slides you to
**Angles**.

Presets: save a settings combination as a named preset ("Engineering explainers,
energetic voice, green captions") so making a batch is one click next time.

## 5. The gates (where humans steer)

**Angles (Gate #1).** A deck of glass cards, one per job: the subject, the chosen
lens/format, and 2–3 candidate angles. Per card you can **approve**, **pick a
different angle**, **edit the text**, or **reject**. Batch actions ("approve all
defaults") for speed. Designed to clear ~20 in a couple minutes — the weekly
ritual.

**Publish (Gate #2).** A review surface per finished job: an inline **video
player** (9:16), the **thumbnail**, editable **title/description/hashtags**, the
**similarity score** (so you can see it's distinct from the back catalogue), and
**Approve & Publish** (honouring dry-run/schedule/privacy). Reject sends it back or
discards.

Both gates show provenance (grounding sources, which lens, regen count) so you're
approving with context, not blind.

## 6. Liquid Glass design language

The aesthetic is Apple's 2025 "Liquid Glass": translucent, layered, luminous,
fluid. Principles:

- **Glass panels** — frosted translucency (`backdrop-blur`), content tints through
  (vibrancy), 1px inner-light top border, soft long shadows for elevation.
- **Depth** — 2–3 layers max (background mesh → glass surfaces → focused content).
  Subtle parallax on scroll/hover; never noisy.
- **Light** — a slow-shifting gradient-mesh backdrop; specular highlights that
  respond to motion; accent colour echoes the active caption style.
- **Motion** — spring physics (the same feel as the Remotion captions): cards
  settle, sheets slide up, the dial glides. Calm, not bouncy.
- **Type** — SF Pro on Mac / Inter elsewhere; large, confident headings; generous
  spacing.
- **Adaptive** — light & dark; an accent colour the user can pick.
- **Accessibility (non-negotiable)** — honour *Reduce Transparency* and *Reduce
  Motion*: fall back to solid panels and cross-fades. Maintain text contrast over
  glass with scrims. Full keyboard navigation.

Design tokens (blur radius, glass opacity, highlight, elevation, radius, accent)
live in one theme file so the whole app restyles from a few variables — same
philosophy as `config/surface.yaml` for videos.

## 7. Technical architecture (for when we build)

Shortcutter is a thin, stateless **view + controller** over the pipeline. The pipeline
stays the single source of truth (job records in `jobs/`, config in `config/`).

```
┌──────────────────────────────────────────────┐
│  Shortcutter desktop app                            │
│  ┌────────────────────┐   ┌────────────────┐  │
│  │ React UI (glass)   │ → │ local bridge   │  │
│  │ Home/Create/Gates… │   │ (HTTP/IPC)     │  │
│  └────────────────────┘   └───────┬────────┘  │
└───────────────────────────────────┼───────────┘
                                     ▼
                    Python pipeline (unchanged)
              cli/stages/orchestrator + jobs/ + config/
```

- **Frontend:** **React** (we already use React via Remotion — shared components,
  and the Remotion player can preview videos inline). Glass via CSS
  `backdrop-filter` + a small motion lib.
- **Shell:** **Tauri** (Rust + system webview) for a light, genuinely *native*
  feel and small install — best match for "like opening an application." Electron
  is the fallback if we want pure-JS tooling.
- **Bridge:** a tiny **FastAPI** sidecar (Python) that wraps the existing
  orchestrator/stages and streams job progress (server-sent events) to the UI.
  Rationale: reuse 100% of the pipeline, get real-time stage updates, and keep the
  CLI working unchanged. (MVP could instead shell out to `cli.py` + watch the
  `jobs/` folder — even less new code.)
- **No logic duplication.** The UI never re-implements generation, the similarity
  guard, or the gates — it calls them. Guardrails (dry-run default, originality
  controls, similarity threshold) live in the pipeline, so the GUI *cannot*
  accidentally bypass the 2025-policy protections.

## 8. Phasing (build order, later)

0. **Design** ✅ (this doc + the mockup).
1. **Read-only shell** — the glass app + Home/Queue reading existing `jobs/`. Proves
   the look and the bridge. No generation yet.
2. **The two gates** — Angles + Publish wired to approve/reject. Immediately useful.
3. **Create + settings** — the config editor that launches batches.
4. **Library, scheduling, health (doctor) panel, presets.**
5. **Later:** analytics, trend hints, A/B — same "genuinely future" status as in
   STRATEGY.md §5. The app makes the pipeline usable; it doesn't change the
   monetization-safety order of operations.

The CLI remains first-class throughout (automation, power users, CI).

## 9. Risks & guardrails

- **Don't let the GUI undercut the policy.** The whole point of the pipeline is
  per-video originality + human gates. The app must *encourage* the gates, keep
  dry-run on by default, and never offer a "publish 50 untouched" button.
- **Glass performance.** Blur is GPU-heavy; cap layered blurs, use cheap fallbacks
  on weak GPUs / battery, respect Reduce Transparency.
- **State ownership.** The pipeline owns truth; the UI is a renderer of `job.json`.
  Avoid a second source of state.
- **Cross-platform.** Liquid glass reads as very "Apple," but must degrade
  gracefully on Windows/Linux.

## 10. Decisions & open questions

**Decided:**
- **Name:** **Shortcutter** (Shorts + shortcut).
- **Platform:** **Mac-first** — a notarized `.app`, SF Pro, native vibrancy.
  Windows comes later; glass degrades gracefully when it does.
- **Create screen:** **curated set + "Advanced ⌄" hidden** by default (see §4).

**Still open:**
- **Local-only vs. account** — single-machine app, or eventually cloud sync of jobs?
- **Accent / theme** — one fixed brand accent, or user-pickable?

---

*This is a forward-looking design. Nothing here changes the current pipeline; it
describes the control surface we can build on top of it when ready.*
