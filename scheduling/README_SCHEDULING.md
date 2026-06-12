## Daily 10:00am batch generation (macOS)

This project can be scheduled with `launchd` to run every day at **10:00am**.

> **It does not upload.** The scheduled run only *generates a batch of jobs up to
> the angle gate* (`python cli.py new`). Publishing requires the two human gates
> (`approve-angle`, then `approve-publish`) — automating past them is exactly the
> channel-level inauthenticity pattern STRATEGY.md warns against. Set the batch
> size with `BATCH_COUNT` (default 5).

### 1) Install the LaunchAgent

Copy the plist into your LaunchAgents folder:

```bash
cp "scheduling/com.ozzie.ytshorts.daily.plist" ~/Library/LaunchAgents/
```

Load it:

```bash
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.ozzie.ytshorts.daily.plist
launchctl enable gui/$UID/com.ozzie.ytshorts.daily
```

Check it’s loaded:

```bash
launchctl print gui/$UID/com.ozzie.ytshorts.daily
```

Logs:
- `logs/launchd.out.log`
- `logs/launchd.err.log`
- `logs/scheduled.log`

### 2) Will it run if my laptop is asleep?

**No** — not unless the Mac wakes up.

To wake your Mac every day before the job:

```bash
sudo pmset repeat wakeorpoweron MTWRFSU 09:58:00
```

Notes:
- Works best with the laptop on power.
- If the lid is closed and your Mac can’t wake/run background tasks, the job won’t run.

### 3) Review and publish

After the scheduled batch runs, do the human gates yourself:

```bash
python cli.py angles                  # review proposed angles
python cli.py approve-angle --all     # or per-job with --pick / --edit
python cli.py run --all               # build videos, park at the publish gate
python cli.py publish-queue           # review finished videos
python cli.py approve-publish <id>    # upload (dry-run unless YOUTUBE_DRY_RUN=false)
```

Privacy on upload is controlled by `YOUTUBE_PRIVACY_STATUS`
(`private` | `unlisted` | `public`) in your `.env`.

