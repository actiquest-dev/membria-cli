#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/miguelaprossine/membria-cli"
CONFIG="$ROOT/.config/membria-mcp/mcp-front.json"
ENVFILE="$ROOT/.config/membria-mcp/mcp-front.env"
BIN="/Users/miguelaprossine/membria-cli/bin/mcp-front"
LOG="/tmp/mcp-front.log"
PIDFILE="/tmp/mcp-front.pid"

cmd=${1:-}

start() {
  if [[ ! -f "$ENVFILE" ]]; then
    echo "env missing: $ENVFILE" >&2
    exit 1
  fi
  if [[ ! -f "$CONFIG" ]]; then
    echo "config missing: $CONFIG" >&2
    exit 1
  fi
  set -a
  # shellcheck disable=SC1090
  source "$ENVFILE"
  set +a
  nohup "$BIN" -config "$CONFIG" > "$LOG" 2>&1 &
  echo $! > "$PIDFILE"
  disown || true
  echo "started: pid $(cat $PIDFILE)"
}

stop() {
  if [[ -f "$PIDFILE" ]]; then
    kill "$(cat $PIDFILE)" 2>/dev/null || true
    rm -f "$PIDFILE"
  fi
  pkill -f "mcp-front" 2>/dev/null || true
  echo "stopped"
}

status() {
  if pgrep -fl mcp-front >/dev/null 2>&1; then
    echo "running"
  else
    echo "stopped"
  fi
}

case "$cmd" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) tail -n 200 "$LOG" ;;
  *) echo "usage: $0 {start|stop|restart|status|logs}"; exit 2;;
esac
