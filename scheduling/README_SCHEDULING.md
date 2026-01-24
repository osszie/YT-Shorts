## Daily 10:00am auto-run (macOS)

This project can be scheduled with `launchd` to run every day at **10:00am**.

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

### 3) Change privacy

Edit `scheduling/com.ozzie.ytshorts.daily.plist`:
- `YOUTUBE_PRIVACY_STATUS`: `private` | `unlisted` | `public`

Then reload:

```bash
launchctl bootout gui/$UID/com.ozzie.ytshorts.daily || true
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.ozzie.ytshorts.daily.plist
```

