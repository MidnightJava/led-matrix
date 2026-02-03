#!/usr/bin/env bash
set -euo pipefail

# ---------------- Config ----------------
BASE_CMD="inputmodule-control led-matrix"
EQ_CMD="$BASE_CMD --input-eq"
FALLBACK_CMD="$BASE_CMD --random-eq"
CHECK_INTERVAL=1
EQ_PID=""
CLEANUP_FLAG=0

# ---------------- Helpers ----------------

log() { echo "[$(date +'%H:%M:%S')] $*"; }

pactl_ok() {
    pactl info >/dev/null 2>&1
}

wait_for_pactl() {
    for _ in {1..20}; do
        pactl_ok && return 0
        sleep 0.25
    done
    return 1
}

current_sink() {
    pactl_ok || return 1
    pactl info | sed -n 's/^Default Sink: //p'
}

monitor_name_for_sink() {
    local sink="$1"
    echo "${sink}.monitor"
}

wait_for_monitor_running() {
    local monitor="$1"
    for _ in {1..50}; do
        # Check if the monitor exists in pactl sources
        if pactl list short sources | awk '{print $2}' | grep -qx "$monitor"; then
            return 0
        fi
        sleep 0.1
    done
    return 1
}

set_default_source() {
    local monitor="$1"
    pactl set-default-source "$monitor" || true
}

sink_type() {
    case "$1" in
        *headphone*|*Audio_Expansion*) echo "headphones" ;;
        *analog-stereo*)       echo "speakers" ;;
         *bluez*)               echo "bluetooth" ;;
        *)                     echo "unknown" ;;
    esac
}

fade_out() {
    # Small pause to simulate fade
    sleep 0.2
}

fade_in() {
    sleep 0.2
}

notify_sink() {
    local type="$1"
    log "Notifying sink change: $type"
    fade_out
    sleep 0.1
    fade_in
}

start_eq() {
    stop_eq
    if pactl_ok; then
        $EQ_CMD &
    else
        $FALLBACK_CMD &
    fi
    EQ_PID=$!
}

stop_eq() {
    # Kill the process we tracked
    [[ -n "${EQ_PID:-}" ]] && kill "$EQ_PID" >/dev/null 2>&1 || true

    # Also make sure no stray processes remain
    pkill -f "${BASE_CMD}" >/dev/null 2>&1 || true

    # Reset EQ_PID
    EQ_PID=""
}


start_fallback() {
    stop_eq
    $FALLBACK_CMD >/dev/null 2>&1 &
    EQ_PID=$!
}

visual_cue() {
    local type="$1"
    case "$type" in
        speakers)
            ${BASE_CMD} --pattern all-on >/dev/null 2>&1
            ;;
        headphones)
            ${BASE_CMD} --pattern zigzag >/dev/null 2>&1
            ;;
        bluetooth)
            ${BASE_CMD} --pattern gradient >/dev/null 2>&1
            ;;
        *)
            ${BASE_CMD} --pattern gradient >/dev/null 2>&1
            ;;
    esac

    # Keep cue visible briefly
    sleep 0.6
}


# ---------------- Cleanup ----------------

cleanup() {
    # Ctrl-C will trigger two traps
    if [ $CLEANUP_FLAG -eq 1 ]; then return; fi
    CLEANUP_FLAG=1
    log "Restoring original input source: $ORIG_SOURCE"
    # stop_eq
    if pactl_ok; then
        pactl set-default-source "$ORIG_SOURCE" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM

# ---------------- Startup ----------------

ORIG_SOURCE=$(pactl info | sed -n 's/^Default Source: //p')
[[ -z "$ORIG_SOURCE" ]] && log "No original source found" && exit 1

log "Original input source: $ORIG_SOURCE"

CURRENT_SINK="$(current_sink)"
MONITOR="$(monitor_name_for_sink "$CURRENT_SINK")"

set_default_source "$MONITOR"

if wait_for_monitor_running "$MONITOR"; then
    log "→ Monitor ready: $MONITOR"
    # start_eq
else
    log "⚠ Monitor not ready, using fallback EQ"
    # start_fallback
fi

# ---------------- Main Loop ----------------

pactl subscribe | while read -r line; do
    case "$line" in
        *"on server"*|*"on sink"*)
            NEW_SINK="$(current_sink)"
            if [[ "$NEW_SINK" != "$CURRENT_SINK" && -n "$NEW_SINK" ]]; then
                log "🔄 Sink change detected → $NEW_SINK"

                # stop_eq

                SINK_TYPE=$(sink_type "$NEW_SINK")
                # fade_out
                # visual_cue "$SINK_TYPE"
                # fade_in

                MONITOR="$(monitor_name_for_sink "$NEW_SINK")"
                log "→ Input now follows: $MONITOR"
                set_default_source "$MONITOR"

                if wait_for_monitor_running "$MONITOR"; then
                    # start_eq
                    CURRENT_SINK="$NEW_SINK"
                # else
                #     log "⚠ Monitor never reached RUNNING/IDLE, using fallback"
                #     # start_fallback
                fi

                # CURRENT_SINK="$NEW_SINK"
            fi
            ;;
    esac
done &
SUB_PID=$!

# Wait for subscription loop
wait "$SUB_PID"
