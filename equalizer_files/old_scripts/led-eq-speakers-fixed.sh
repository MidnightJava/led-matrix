#!/usr/bin/env bash
set -euo pipefail

############################
# CONFIG
############################

EQ_CMD="inputmodule-control led-matrix --input-eq"
FALLBACK_CMD="inputmodule-control led-matrix --random-eq"

CHECK_INTERVAL=1        # seconds between sink polls
MONITOR_TIMEOUT=5       # seconds to wait for monitor readiness

############################
# STATE
############################

ORIGINAL_SOURCE=""
EQ_PID=""
CURRENT_SINK=""

############################
# UTILS
############################

log() {
  echo "[$(date +%H:%M:%S)] $*"
}

fade_out() {
  for _ in {1..3}; do
    inputmodule-control led-matrix --test off >/dev/null 2>&1
    sleep 0.05
  done
}

fade_in() {
  inputmodule-control led-matrix --test off >/dev/null 2>&1
  sleep 0.05
}

notify_sink() {
  local sink_type="$1"

  case "$sink_type" in
    headphones)
      inputmodule-control led-matrix --test vertical >/dev/null 2>&1
      ;;
    speakers)
      inputmodule-control led-matrix --test horizontal >/dev/null 2>&1
      ;;
    *)
      inputmodule-control led-matrix --test blink >/dev/null 2>&1
      ;;
  esac

  sleep 0.4
}

get_default_sink() {
  pactl info | awk -F': ' '/Default Sink/ {print $2}'
}

get_default_source() {
  pactl info | awk -F': ' '/Default Source/ {print $2}'
}

set_default_source() {
  pactl set-default-source "$1"
}

monitor_name_for_sink() {
  echo "${1}.monitor"
}

monitor_state() {
  pactl list short sources | awk -v src="$1" '$2 == src {print $7}'
}

wait_for_monitor_running() {
  local monitor="$1"
  local elapsed=0

  while (( elapsed < MONITOR_TIMEOUT )); do
    state="$(monitor_state "$monitor" || true)"

    case "$state" in
      RUNNING|IDLE)
        return 0
        ;;
    esac

    sleep 1
    ((elapsed++))
  done

  return 1
}

stop_eq() {
  if [[ -n "${EQ_PID:-}" ]] && kill -0 "$EQ_PID" 2>/dev/null; then
    log "Stopping EQ (pid $EQ_PID)"
    kill "$EQ_PID"
    wait "$EQ_PID" 2>/dev/null || true
  fi
  EQ_PID=""
}

start_eq() {
  log "Starting EQ"
  $EQ_CMD >/dev/null 2>&1 &
  EQ_PID=$!
}

start_fallback() {
  log "Starting fallback EQ"
  $FALLBACK_CMD >/dev/null 2>&1 &
  EQ_PID=$!
}

cleanup() {
  log "Cleaning up"
  stop_eq
  [[ -n "$ORIGINAL_SOURCE" ]] && set_default_source "$ORIGINAL_SOURCE"
  exit 0
}

trap cleanup INT TERM

############################
# INIT
############################

if ! pactl info >/dev/null 2>&1; then
  log "pactl unavailable, starting fallback EQ"
  start_fallback
  wait
fi

ORIGINAL_SOURCE="$(get_default_source)"
log "Original input source: $ORIGINAL_SOURCE"

############################
# MAIN LOOP
############################

while true; do
  NEW_SINK="$(get_default_sink)"

  if [[ "$NEW_SINK" != "$CURRENT_SINK" ]]; then
    log "🔄 Sink change detected → $NEW_SINK"

    stop_eq

    MONITOR="$(monitor_name_for_sink "$NEW_SINK")"
    log "→ Input now follows: $MONITOR"

    set_default_source "$MONITOR"

    if wait_for_monitor_running "$MONITOR"; then
      log "✅ Monitor ready"
      start_eq
    else
      log "⚠ Monitor never reached RUNNING/IDLE"
      start_fallback
    fi

    CURRENT_SINK="$NEW_SINK"
  fi

  sleep "$CHECK_INTERVAL"
done
