#!/usr/bin/env bash
set -euo pipefail

# Runs the full pipeline + upload.
# Intended to be invoked by macOS launchd on a schedule.

ROOT="/Users/ozzie/Desktop/AI Youtube Shorts/yt-shorts-agent"
VENV="$ROOT/.venv"

cd "$ROOT"

# Activate venv
source "$VENV/bin/activate"

# Ensure logs dir exists
mkdir -p "$ROOT/logs"

# Defaults: upload unlisted (safer). Override in your launchd plist or environment if desired.
export YOUTUBE_PRIVACY_STATUS="${YOUTUBE_PRIVACY_STATUS:-unlisted}"

ts="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$ts] Starting scheduled run (privacy=$YOUTUBE_PRIVACY_STATUS)" >> "$ROOT/logs/scheduled.log"

python "$ROOT/scripts/run_all.py" --upload --no-dry-run >> "$ROOT/logs/scheduled.log" 2>&1

ts="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$ts] Finished scheduled run" >> "$ROOT/logs/scheduled.log"

