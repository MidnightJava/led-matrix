#!/usr/bin/env bash
# No longer used. Tracks current sink and sets current source to its monitor. Now handled by visualize.py,
# integrated with LED notificaiton of source switch.
set -euo pipefail

# ---------------- Config ----------------
BASE_CMD="inputmodule-control --serial-dev /dev/ttyACM0 led-matrix"
EQ_PID=""
CLEANUP_FLAG=0

# ---------------- Helpers ----------------

log() { echo "[$(date +'%H:%M:%S')] $*"; }

pactl_ok() {
    pactl info >/dev/null 2>&1
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

notify_sink() {
    local type="$1"
    log "Notifying sink change: $type"
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
    EQ_PID=$!
}


# ---------------- Cleanup ----------------

cleanup() {
    # Ctrl-C will trigger two traps
    if [ $CLEANUP_FLAG -eq 1 ]; then return; fi
    CLEANUP_FLAG=1
    log "Restoring original input source: $ORIG_SOURCE"
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
else
    log "⚠ Monitor not ready"
fi

# ---------------- Main Loop ----------------

pactl subscribe | while read -r line; do
    case "$line" in
        *"on server"*|*"on sink"*)
            NEW_SINK="$(current_sink)"
            if [[ "$NEW_SINK" != "$CURRENT_SINK" && -n "$NEW_SINK" ]]; then
                log "🔄 Sink change detected → $NEW_SINK"

                SINK_TYPE=$(sink_type "$NEW_SINK")
                # for _ in {1..5}; do
                #     visual_cue "$SINK_TYPE"
                #     sleep 0.01
                # done
                [[ -n "${EQ_PID:-}" ]] && kill "$EQ_PID" >/dev/null 2>&1 || true
                EQ_PID=""


                MONITOR="$(monitor_name_for_sink "$NEW_SINK")"
                log "→ Input now follows: $MONITOR"
                set_default_source "$MONITOR"

                if wait_for_monitor_running "$MONITOR"; then
                    CURRENT_SINK="$NEW_SINK"
                fi
            fi
            ;;
    esac
done &
SUB_PID=$!

# Wait for subscription loop
wait "$SUB_PID"
