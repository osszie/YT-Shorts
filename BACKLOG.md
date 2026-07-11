# Backlog

The daily loop works from this list, top-down. Check items off (move to *Done*)
as they land. Sourced from the Fable audit (2026-06-17) + the strategy's
deferred items.

## Now (bugs / correctness)

(empty — audit items all landed 2026-06-17, see Done)

## Next (quality / polish)

(empty — audit items all landed 2026-06-17, see Done)

## Later (bigger, schedule as their own days)

- [ ] **Migrate `google-generativeai` → `google-genai`** (upstream EOL; contained
  to `pipeline/providers/gemini.py` now that providers are abstracted).
- [ ] **Shortcutter Phase 1** — read-only glass shell over `jobs/` (React + Tauri
  + FastAPI bridge, per `docs/LAUNCHER_DESIGN.md` §8).
- [ ] Clip layouts: multi-speaker / split-screen; B-roll.
- [ ] "Write or Clip" home-screen mockup.
- [ ] Per-feature branches instead of the single long-lived work branch.

## Needs the user's machine (not doable in the cloud sandbox)

- [ ] First real generated Short (Edge-TTS + Whisper live).
- [ ] Clip a real Twitch VOD end-to-end (yt-dlp + OpenCV live).
- [ ] First real YouTube upload through the publish gate.
- [ ] Rotate the Gemini API keys pasted in chat.

## Deferred by strategy (don't start until videos are live)

- Analytics, trend detection, A/B testing, multi-language.

## Done

- (2026-06-17) Fable audit of the whole project — findings feed this list.
- (2026-06-17) **All audit fixes landed** (daily loop, day 1):
  highlight chunking + overlap dedupe + coverage logging (whole-VOD analysis);
  regen crash path caught (job fails cleanly on 429 during regen);
  clip captions `done()` requires both artifacts + stale `reframed.mp4` probe
  fixed; `approve-angle`/`approve-publish` usage instead of traceback; TLS
  workaround scoped to the Whisper model download; `WHISPER_MODEL` env;
  `zod@4.3.6` pinned (mismatch warning gone, tsc clean); `RENDER_ENGINE` read
  at run time; mode-aware `status` + `publish-queue`; similarity-catalog
  policy documented. Tests 85 → 91.
