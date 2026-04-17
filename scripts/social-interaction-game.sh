#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GAME_DIR="$ROOT_DIR/Exploratory Ideas/social-interaction-game"

activate_venv() {
  local candidates=(
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

  echo "No virtual environment found at .venv/, venv/, or env/." >&2
  exit 1
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
  local server_pid="$1"
  local url="$2"
  local attempt

  for attempt in {1..20}; do
    if ! kill -0 "$server_pid" >/dev/null 2>&1; then
      return 1
    fi

    if command -v curl >/dev/null 2>&1; then
      if curl --silent --fail "$url" >/dev/null 2>&1; then
        return 0
      fi
    else
      sleep 0.25
    fi

    sleep 0.25
  done

  return 0
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/social-interaction-game.sh list
  ./scripts/social-interaction-game.sh cli [--scenario SCENARIO_ID]
  ./scripts/social-interaction-game.sh cli --procedural-seed 7
  ./scripts/social-interaction-game.sh ai [--scenario SCENARIO_ID]
  ./scripts/social-interaction-game.sh web [--port 8765] [--no-browser]
  ./scripts/social-interaction-game.sh test

Commands:
  list    List the hand-authored scenarios
  cli     Play manually in the terminal
  ai      Let the baseline AI play in the terminal
  web     Launch the browser UI and local API server
  test    Run the lightweight reward tests
EOF
}

activate_venv

command="${1:-}"
shift || true

case "$command" in
  list)
    python3 "$GAME_DIR/play.py" --list "$@"
    ;;
  cli)
    python3 "$GAME_DIR/play.py" "$@"
    ;;
  ai)
    python3 "$GAME_DIR/play.py" --auto "$@"
    ;;
  web)
    port="8765"
    open_flag="yes"
    extra_args=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --port)
          port="${2:?Missing value for --port}"
          extra_args+=("$1" "$2")
          shift 2
          ;;
        --no-browser)
          open_flag="no"
          shift
          ;;
        *)
          extra_args+=("$1")
          shift
          ;;
      esac
    done

    if [[ ${#extra_args[@]} -gt 0 ]]; then
      python3 "$GAME_DIR/server.py" "${extra_args[@]}" &
    else
      python3 "$GAME_DIR/server.py" &
    fi
    server_pid=$!
    trap 'kill "$server_pid" >/dev/null 2>&1 || true' EXIT INT TERM
    url="http://127.0.0.1:${port}"
    if ! wait_for_server "$server_pid" "$url"; then
      echo "Social Interaction Game failed to start on $url" >&2
      wait "$server_pid" || true
      exit 1
    fi
    echo "Social Interaction Game is running at $url"
    if [[ "$open_flag" == "yes" ]]; then
      open_browser "$url"
    fi
    wait "$server_pid"
    ;;
  test)
    python3 "$GAME_DIR/run_tests.py" "$@"
    ;;
  *)
    usage
    exit 1
    ;;
esac
