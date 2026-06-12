#!/usr/bin/env bash
set -euo pipefail

# Scheduled batch generation.
#
# IMPORTANT: this does NOT upload. STRATEGY.md requires two human gates (angle +
# publish), so the scheduler only fills the queue up to the ANGLE gate. A human
# then batches `approve-angle`, `run --all`, reviews `publish-queue` and
# `approve-publish`. Automating past the gates is exactly the channel-level
# inauthenticity pattern the 2025 policy demonetizes.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"
COUNT="${BATCH_COUNT:-5}"

cd "$ROOT"
[ -f "$VENV/bin/activate" ] && source "$VENV/bin/activate"
mkdir -p "$ROOT/logs"

ts="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$ts] Generating batch of $COUNT job(s) to the angle gate" >> "$ROOT/logs/scheduled.log"

python "$ROOT/cli.py" new --count "$COUNT" >> "$ROOT/logs/scheduled.log" 2>&1

ts="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[$ts] Batch ready. Review: python cli.py angles" >> "$ROOT/logs/scheduled.log"
