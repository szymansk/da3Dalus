#!/usr/bin/env bash
# Run any command while an RSS watchdog hard-kills runaway vspaero
# processes (>6 GB) — see VSPAERO_API.md lesson 5. ulimit -v is NOT
# enforced on macOS, so a real watchdog is the only reliable guard.
#
# Usage:
#   ./run_with_watchdog.sh "PYTHONPATH=. poetry run python scripts/vspaero_benchmark/run_all.py"
set -uo pipefail

KILL_RSS_KB=${KILL_RSS_KB:-6291456}   # 6 GB
CMD="$*"

ulimit -v 8388608 2>/dev/null || true  # best-effort (no-op on macOS)

(
  while true; do
    for vpid in $(pgrep -x vspaero 2>/dev/null); do
      rss=$(ps -o rss= -p "$vpid" 2>/dev/null | tr -d ' ')
      if [ -n "$rss" ] && [ "$rss" -gt "$KILL_RSS_KB" ]; then
        echo "!!! WATCHDOG: vspaero pid=$vpid RSS=${rss}KB > ${KILL_RSS_KB}KB — KILLING" >&2
        kill -9 "$vpid" 2>/dev/null
      fi
    done
    sleep 0.5
  done
) &
WATCH=$!
trap 'kill "$WATCH" 2>/dev/null' EXIT

bash -c "$CMD"
RC=$?
kill "$WATCH" 2>/dev/null
exit $RC
