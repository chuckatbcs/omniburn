#!/usr/bin/env bash
# Setup automated periodic model and pricing sync for OmniBurn.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TRACKER_DIR="${OMNIBURN_DIR:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"
CLI_PATH="${OMNIBURN_CLI_PATH:-$TRACKER_DIR/ai-burn}"
mkdir -p "$TRACKER_DIR/.runtime"

# Cron entry to run sync every 6 hours
CRON_JOB="0 */6 * * * $CLI_PATH sync >> $TRACKER_DIR/.runtime/sync.log 2>&1"

(crontab -l 2>/dev/null | grep -v "ai-burn sync" ; echo "$CRON_JOB") | crontab -
echo "✓ Scheduled recurring sync job every 6 hours in crontab:"
crontab -l | grep "ai-burn"
