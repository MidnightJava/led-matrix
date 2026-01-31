#!/usr/bin/env bash
set -euo pipefail

EQ_CMD="inputmodule-control led-matrix --input-eq"
CHECK_INTERVAL=0.5  # seconds
MONITOR_TIMEOUT=5       # seconds to wait for monitor readiness

# ---------------- HELPERS ----------------
log() { echo "[$(date '+%H:%M:%S')] $*"; }

pactl_ok() { pactl info >/dev/null 2>&1; }

get_default_sink() { pactl_ok || return 1; pactl info | sed -n 's/^Default Sink: //p'; }
monitor_name_for_sink() { echo "${1}.monitor"; }

set_default_source() {
    local source="$1"
    pactl set-default-source "$source" >/dev/null 2>&1
}


sink_type() {
    case "$1" in
    *headphone*|*headset*) echo "headphones" ;;
    *analog-stereo*)       echo "speakers" ;;
    *)                     echo "unknown" ;;
    esac
}

wait_for_monitor() {
  local monitor="$1"
  for _ in {1..40}; do
    pactl list short sources | awk '{print $2}' | grep -qx "$monitor" && return 0
    sleep 0.25
  done
  return 1
}

monitor_state() {
  pactl list short sources | awk -v src="$1" '$2 == src {print $7}'
}

wait_for_monitor_running() {
    local monitor="$1"
    local max_wait=30   # increase from 2-3s to 30s
    local waited=0

    while ! pactl list short sources | awk '{print $2}' | grep -qx "$monitor"; do
        sleep 0.5
        ((waited+=1))
        if (( waited*5 >= max_wait )); then
            return 1
        fi
    done

    # Optional: extra wait until the monitor actually reports RUNNING
    # Could use `pw-top` or PipeWire API for more precision
    sleep 10
    return 0
}


fade_out() {
  for _ in {1..3}; do
    inputmodule-control led-matrix --pattern all-on >/dev/null 2>&1
    sleep 0.05
    inputmodule-control led-matrix --pattern percentage >/dev/null 2>&1  # or your default EQ pattern

    sleep 0.05
  done
}
fade_in() { sleep 0.05; }

notify_sink() {
  case "$1" in
    headphones) inputmodule-control led-matrix --pattern percentage >/dev/null 2>&1 ;;
    speakers)   inputmodule-control led-matrix --pattern double-gradient >/dev/null 2>&1 ;;
    *)          inputmodule-control led-matrix --pattern all-on >/dev/null 2>&1
                sleep 0.3
                inputmodule-control led-matrix --random-eq >/dev/null 2>&1 ;;
esac
sleep 0.4
}

start_eq() {
  if pactl_ok; then
    $EQ_CMD &
    EQ_PID=$!
  else
    inputmodule-control led-matrix --random-eq >/dev/null 2>&1 &
    EQ_PID=$!
  fi
}

# stop_eq() {
#   [[ -n "${EQ_PID:-}" ]] && kill "$EQ_PID" >/dev/null 2>&1 || true
#   wait "${EQ_PID:-}" 2>/dev/null || true
#   EQ_PID=""
# }

stop_eq() {
    if [[ -n "$EQ_PID" ]]; then
        kill "$EQ_PID" >/dev/null 2>&1 || true
        wait "$EQ_PID" 2>/dev/null || true
        EQ_PID=""
    fi
}

start_fallback() {
  inputmodule-control led-matrix --random-eq >/dev/null 2>&1 &
  EQ_PID=$!
}

# ---------------- STARTUP ----------------
ORIG_SOURCE=$(pactl info | sed -n 's/^Default Source: //p')
[[ -z "$ORIG_SOURCE" ]] && exit 1
log "Original input source: $ORIG_SOURCE"

EQ_PID=""
CURRENT_SINK="$(get_default_sink)"
MONITOR="$(monitor_name_for_sink "$CURRENT_SINK")"

if ! wait_for_monitor_running "$MONITOR"; then
    echo "⚠ Monitor not ready, retrying in 2s..."
    sleep 2
    wait_for_monitor_running "$MONITOR" || start_fallback
fi
set_default_source "$MONITOR"
start_eq

# ---------------- CLEANUP ----------------
cleanup() {
  log "Restoring original source: $ORIG_SOURCE"
  stop_eq
  pactl_ok && pactl set-default-source "$ORIG_SOURCE" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# ---------------- MAIN LOOP ----------------
while true; do
  NEW_SINK="$(get_default_sink)"
  if [[ "$NEW_SINK" != "$CURRENT_SINK" && -n "$NEW_SINK" ]]; then
    log "🔄 Sink change detected → $NEW_SINK"

    SINK_TYPE="$(sink_type "$NEW_SINK")"
    MONITOR="$(monitor_name_for_sink "$NEW_SINK")"
    log "→ Waiting for monitor: $MONITOR"

    if wait_for_monitor_running "$MONITOR"; then
      log "✅ Monitor ready"
      set_default_source "$MONITOR"

      fade_out
      notify_sink "$SINK_TYPE"

      stop_eq
      start_eq
      fade_in
    else
      log "⚠ Monitor never reached RUNNING/IDLE — fallback EQ"
      stop_eq
      start_fallback
    fi

    CURRENT_SINK="$NEW_SINK"
  fi
  sleep "$CHECK_INTERVAL"
done
