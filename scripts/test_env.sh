#!/usr/bin/env bash
# Isolated da3Dalus test environment: own worktree, own SQLite DB, own API server.
#
# Built for cloud/CI containers and local trials where the real DB must not be touched.
# Everything lives under $TESTENV_DIR (default /tmp/da3dalus-testenv); the checkout you
# run this from is never written to (reference-model imports copy airfoils into
# components/, which is tracked - so they go into the worktree instead).
#
#   scripts/test_env.sh up [REF]        worktree at REF (default HEAD), deps, fresh DB, tmp/
#   scripts/test_env.sh import KEY...   import reference models (scripts/canon_checks/reference_fleet/KEY)
#   scripts/test_env.sh start           start the API in the background, wait until it answers
#   scripts/test_env.sh run CMD...      run CMD in the worktree with the env's python and DB
#   scripts/test_env.sh stop            stop the API
#   scripts/test_env.sh status          worktree, DB, server
#   scripts/test_env.sh down            stop, remove worktree and DB
#
# Env: TESTENV_DIR, TESTENV_PORT (default 8011).
# The API URL is printed by `start`; `run` exports it as DA3DALUS_API.
set -euo pipefail

REPO="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
DIR="${TESTENV_DIR:-/tmp/da3dalus-testenv}"
PORT="${TESTENV_PORT:-8011}"
WT="$DIR/repo"
DB="$DIR/db/test.db"
PIDFILE="$DIR/server.pid"
LOG="$DIR/server.log"
API="http://127.0.0.1:$PORT"

die() { echo "test_env: $*" >&2; exit 1; }

venv_bin() {
  # The worktree shares the main checkout's Poetry venv (poetry keys venvs by path).
  local p
  p="$(cd "$REPO" && poetry env info -p 2>/dev/null)" || true
  if [ -z "$p" ] || [ ! -x "$p/bin/python" ]; then
    (cd "$REPO" && poetry install --no-interaction >&2)
    p="$(cd "$REPO" && poetry env info -p)"
  fi
  echo "$p/bin"
}

in_env() {
  [ -d "$WT" ] || die "keine Umgebung - erst 'up'"
  local bin; bin="$(venv_bin)"
  (cd "$WT" && exec env PATH="$bin:$PATH" PYTHONPATH="$WT" \
     SQLALCHEMY_DATABASE_URL="sqlite:///$DB" DA3DALUS_API="$API" "$@")
}

server_pid() {
  [ -f "$PIDFILE" ] || return 1
  local pid; pid="$(cat "$PIDFILE")"
  kill -0 "$pid" 2>/dev/null && echo "$pid"
}

cmd_up() {
  local ref="${1:-HEAD}"
  [ -e "$WT" ] && die "$WT existiert schon - erst 'down'"
  mkdir -p "$DIR/db"
  git -C "$REPO" worktree add --detach "$WT" "$ref" >/dev/null
  mkdir -p "$WT/tmp"
  in_env alembic upgrade head >/dev/null 2>&1 || { in_env alembic upgrade head; die "alembic fehlgeschlagen"; }
  echo "Umgebung bereit: $WT @ $(git -C "$WT" rev-parse --short HEAD), DB $DB"
}

cmd_import() {
  [ $# -gt 0 ] || die "import KEY... (z.B. bryan)"
  for key in "$@"; do
    in_env python scripts/canon_checks/reference_fleet/import_to_db.py "$key"
  done
}

cmd_start() {
  if pid="$(server_pid)"; then echo "API laeuft schon: $API (PID $pid)"; return; fi
  curl -s -o /dev/null "$API/docs" && die "Port $PORT ist belegt - TESTENV_PORT setzen"
  venv_bin >/dev/null  # install deps in the foreground, not inside the background job
  # The server writes its own PID ($! would be a bash subshell); setsid gives it its own
  # process group (setsid does not fork here, so the PID stays) and 'stop' kills just that.
  rm -f "$PIDFILE"
  in_env sh -c 'echo $$ >"$0"; exec setsid uvicorn app.main:app --host 127.0.0.1 --port "$1"' \
    "$PIDFILE" "$PORT" >"$LOG" 2>&1 </dev/null &
  for _ in $(seq 1 120); do
    if curl -sf -o /dev/null "$API/docs"; then echo "API bereit: $API (Log $LOG)"; return; fi
    if [ -s "$PIDFILE" ] && ! server_pid >/dev/null; then tail -20 "$LOG"; die "API-Start fehlgeschlagen"; fi
    sleep 1
  done
  tail -20 "$LOG"; die "API antwortet nicht nach 120 s"
}

cmd_stop() {
  if pid="$(server_pid)"; then
    kill -- "-$pid" 2>/dev/null || kill "$pid"
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
    echo "API gestoppt"
  fi
  rm -f "$PIDFILE"
}

cmd_status() {
  if [ -d "$WT" ]; then echo "Worktree: $WT @ $(git -C "$WT" rev-parse --short HEAD)"; else echo "Worktree: -"; fi
  if [ -f "$DB" ]; then echo "DB: $DB"; else echo "DB: -"; fi
  if pid="$(server_pid)"; then echo "API: $API (PID $pid)"; else echo "API: aus"; fi
}

cmd_down() {
  cmd_stop
  [ -d "$WT" ] && git -C "$REPO" worktree remove --force "$WT"
  rm -rf "$DIR"
  echo "Umgebung entfernt"
}

case "${1:-}" in
  up) shift; cmd_up "$@" ;;
  import) shift; cmd_import "$@" ;;
  start) cmd_start ;;
  run) shift; in_env "$@" ;;
  stop) cmd_stop ;;
  status) cmd_status ;;
  down) cmd_down ;;
  *) sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
