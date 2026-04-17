#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GAME_DIR="$ROOT_DIR/attempt1/doc_edit_game_v2"
STATE_FILE="/tmp/open-env-meta-doc-edit-game.state"
LOG_FILE="/tmp/open-env-meta-doc-edit-game.log"

HOST="127.0.0.1"
PORT="8877"
OPEN_BROWSER="no"
UI_MODE="modern"

activate_venv() {
  local candidates=(
    "$GAME_DIR/.venv/bin/activate"
    "$ROOT_DIR/.venv/bin/activate"
    "$ROOT_DIR/venv/bin/activate"
    "$ROOT_DIR/env/bin/activate"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      # shellcheck disable=SC1090
      source "$candidate"
      return 0
    fi
  done

  echo "No virtual environment found for DocEdit Game V2." >&2
  echo "Checked:" >&2
  printf '  - %s\n' "${candidates[@]}" >&2
  exit 1
}

save_state() {
  local pid="$1"
  cat >"$STATE_FILE" <<EOF
PID=$pid
HOST=$HOST
PORT=$PORT
URL=http://$HOST:$PORT
UI_MODE=$UI_MODE
LOG_FILE=$LOG_FILE
GAME_DIR=$GAME_DIR
EOF
}

load_state() {
  if [[ -f "$STATE_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$STATE_FILE"
    return 0
  fi
  return 1
}

clear_state() {
  rm -f "$STATE_FILE"
}

is_running() {
  load_state || return 1
  [[ -n "${PID:-}" ]] && kill -0 "$PID" >/dev/null 2>&1
}

open_browser() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 || true
  fi
}

wait_for_server() {
  local pid="$1"
  local url="$2"
  local attempt

  for attempt in {1..40}; do
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      return 1
    fi

    if curl --silent --fail "$url/health" >/dev/null 2>&1; then
      return 0
    fi

    sleep 0.25
  done

  return 1
}

print_usage() {
  cat <<'EOF'
Usage:
  ./scripts/doc-edit-game.sh run [--port 8877] [--host 127.0.0.1] [--ui modern|classic]
  ./scripts/doc-edit-game.sh start [--port 8877] [--host 127.0.0.1] [--open] [--ui modern|classic]
  ./scripts/doc-edit-game.sh stop
  ./scripts/doc-edit-game.sh restart [--port 8877] [--host 127.0.0.1] [--open] [--ui modern|classic]
  ./scripts/doc-edit-game.sh status
  ./scripts/doc-edit-game.sh logs [-f]
  ./scripts/doc-edit-game.sh smoke
  ./scripts/doc-edit-game.sh open

Commands:
  run      Launch the DocEdit browser UI and OpenEnv API in the foreground
  start    Launch the DocEdit browser UI and OpenEnv API in the background
  stop     Stop the background DocEdit server
  restart  Restart the background DocEdit server
  status   Show whether the server is running and where to open it
  logs     Print recent logs, or pass -f to follow them
  smoke    Check the browser route, human game API, and OpenEnv API
  open     Open the browser to the running game URL
EOF
}

parse_server_flags() {
  HOST="127.0.0.1"
  PORT="8877"
  OPEN_BROWSER="no"
  UI_MODE="modern"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --port)
        PORT="${2:?Missing value for --port}"
        shift 2
        ;;
      --host)
        HOST="${2:?Missing value for --host}"
        shift 2
        ;;
      --open)
        OPEN_BROWSER="yes"
        shift
        ;;
      --ui)
        UI_MODE="${2:?Missing value for --ui}"
        if [[ "$UI_MODE" != "modern" && "$UI_MODE" != "classic" ]]; then
          echo "Unknown UI mode: $UI_MODE" >&2
          print_usage
          exit 1
        fi
        shift 2
        ;;
      *)
        echo "Unknown option: $1" >&2
        print_usage
        exit 1
        ;;
    esac
  done
}

start_server() {
  parse_server_flags "$@"

  if is_running; then
    echo "DocEdit game is already running at $URL (PID $PID)."
    return 0
  fi

  clear_state
  activate_venv
  local pid
  local previous_dir
  previous_dir="$(pwd)"
  cd "$GAME_DIR"
  nohup env DOCEDIT_UI_DEFAULT="$UI_MODE" python -m uvicorn server.app:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 < /dev/null &
  pid="$!"
  disown "$pid" 2>/dev/null || true
  cd "$previous_dir"
  save_state "$pid"

  if ! wait_for_server "$pid" "http://$HOST:$PORT"; then
    echo "DocEdit game failed to start. Recent logs:" >&2
    tail -n 40 "$LOG_FILE" >&2 || true
    clear_state
    exit 1
  fi

  echo "DocEdit game is running."
  echo "URL: http://$HOST:$PORT"
  echo "Default UI: $UI_MODE"
  echo "Logs: $LOG_FILE"
  echo "Modern UI: http://$HOST:$PORT/modern"
  echo "Classic UI: http://$HOST:$PORT/classic"
  echo "OpenEnv API: http://$HOST:$PORT/api/openenv"

  if [[ "$OPEN_BROWSER" == "yes" ]]; then
    open_browser "http://$HOST:$PORT/${UI_MODE}"
  fi
}

run_foreground() {
  parse_server_flags "$@"
  activate_venv
  cd "$GAME_DIR"
  exec env DOCEDIT_UI_DEFAULT="$UI_MODE" python -m uvicorn server.app:app --host "$HOST" --port "$PORT"
}

stop_server() {
  if ! is_running; then
    clear_state
    echo "DocEdit game is not running."
    return 0
  fi

  kill "$PID" >/dev/null 2>&1 || true

  for _ in {1..20}; do
    if ! kill -0 "$PID" >/dev/null 2>&1; then
      clear_state
      echo "Stopped DocEdit game."
      return 0
    fi
    sleep 0.25
  done

  echo "Process $PID did not exit after a graceful stop." >&2
  exit 1
}

status_server() {
  if is_running; then
    echo "DocEdit game is running."
    echo "PID: $PID"
    echo "URL: $URL"
    echo "Default UI: ${UI_MODE:-modern}"
    echo "Logs: $LOG_FILE"
    if curl --silent --fail "$URL/health" >/dev/null 2>&1; then
      echo "Health: ok"
    else
      echo "Health: process is up, but /health did not respond"
    fi
    return 0
  fi

  clear_state
  echo "DocEdit game is not running."
}

show_logs() {
  local follow="${1:-}"
  if [[ "$follow" == "-f" ]]; then
    tail -f "$LOG_FILE"
  else
    tail -n 60 "$LOG_FILE"
  fi
}

smoke_test() {
  if ! is_running; then
    echo "DocEdit game is not running. Start it first." >&2
    exit 1
  fi

  echo "Checking browser route..."
  curl --silent --fail -o /dev/null "$URL/"
  echo "  OK: /"

  echo "Checking modern UI..."
  curl --silent --fail -o /dev/null "$URL/modern"
  echo "  OK: /modern"

  echo "Checking classic UI..."
  curl --silent --fail -o /dev/null "$URL/classic"
  echo "  OK: /classic"

  echo "Checking health..."
  curl --silent --fail "$URL/health"
  echo

  echo "Checking human game API..."
  local session_json
  session_json="$(curl --silent --fail -X POST "$URL/api/game/new" -H 'Content-Type: application/json' -d '{"seed":123,"difficulty":2,"domain":"legal"}')"
  local session_id
  session_id="$(printf '%s' "$session_json" | sed -n 's/.*"session_id":"\([^"]*\)".*/\1/p')"
  echo "  OK: /api/game/new created session ${session_id:-unknown}"

  echo "Checking OpenEnv API..."
  curl --silent --fail -o /dev/null "$URL/api/openenv/openapi.json"
  echo "  OK: /api/openenv/openapi.json"
}

open_running_game() {
  if ! is_running; then
    echo "DocEdit game is not running. Start it first." >&2
    exit 1
  fi
  open_browser "$URL/${UI_MODE:-modern}"
  echo "Opened $URL/${UI_MODE:-modern}"
}

command="${1:-}"
shift || true

case "$command" in
  run)
    run_foreground "$@"
    ;;
  start)
    start_server "$@"
    ;;
  stop)
    stop_server
    ;;
  restart)
    parse_server_flags "$@"
    requested_host="$HOST"
    requested_port="$PORT"
    requested_open="$OPEN_BROWSER"
    requested_ui="$UI_MODE"
    stop_server || true
    start_args=(--host "$requested_host" --port "$requested_port")
    if [[ "$requested_open" == "yes" ]]; then
      start_args+=(--open)
    fi
    start_args+=(--ui "$requested_ui")
    start_server "${start_args[@]}"
    ;;
  status)
    status_server
    ;;
  logs)
    show_logs "${1:-}"
    ;;
  smoke)
    smoke_test
    ;;
  open)
    open_running_game
    ;;
  *)
    print_usage
    exit 1
    ;;
esac
