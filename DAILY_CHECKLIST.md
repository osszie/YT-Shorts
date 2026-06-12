# Operating Checklist

The pipeline automates generation and asks you to steer at **two batched gates**.
A typical weekly session:

## 1. Generate a batch (auto → angle gate)
- [ ] `source .venv/bin/activate`
- [ ] `python cli.py new --count 20`
- [ ] `python cli.py status` — confirm jobs are `awaiting_angle`

## 2. Angle gate (batched human input #1)
- [ ] `python cli.py angles` — read the proposed angles
- [ ] For each: `python cli.py approve-angle <id> --pick N` (or `--edit "..."`)
- [ ] Or batch the defaults: `python cli.py approve-angle --all`
- [ ] Reject weak ones: `python cli.py reject <id> --reason "..."`

## 3. Run the automated middle
- [ ] `python cli.py run --all` — script → similarity guard → assets → voice →
      captions → assemble → metadata, parking at the publish gate
- [ ] `python cli.py status` — anything `failed`? `python cli.py show <id>` for the
      error, fix the cause, rerun `python cli.py run <id>` (it resumes, not restarts)

## 4. Publish gate (batched human input #2)
- [ ] `python cli.py publish-queue` — review titles + watch `jobs/<id>/final.mp4`
- [ ] Approve: `python cli.py approve-publish <id>` (uploads; **dry-run** unless
      `YOUTUBE_DRY_RUN=false` in `.env`)

## Notes
- Nothing publishes by accident — uploads are dry-run by default.
- The similarity guard auto-rejects/regenerates scripts too close to past videos.
- No Gemini key set? The spine still runs with deterministic fallbacks.
- Read `STRATEGY.md` before changing any stage.
