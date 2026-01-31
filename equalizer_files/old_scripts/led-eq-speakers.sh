#!/usr/bin/env bash
set -euo pipefail

# ---------------- CONFIG ------------------
EQ_CMD="inputmodule-control led-matrix --input-eq"
CHECK_INTERVAL=1  # seconds between sink checks

# ---------------- HELPERS -----------------

log() {
    echo "$(date +'%H:%M:%S') $*"
}

# Check if pactl is responding
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

# Get current default sink
get_default_sink() {
    pactl_ok || return 1
    pactl info | sed -n 's/^Default Sink: //p'
}

# Map sink to its monitor source
monitor_name_for_sink() {
    local sink="$1"
    echo "${sink}.monitor"
}

# Wait for monitor source to appear
wait_for_monitor_running() {
    local monitor="$1"
    for _ in {1..20}; do
        pactl list short sources | awk '{print $2}' | grep -qx "$monitor" && return 0
        sleep 0.1
    done
    return 1
}

# Set default source
set_default_source() {
    local src="$1"
    pactl_ok || return 1
    pactl set-default-source "$src"
}

# Determine sink type for notifications
sink_type() {
    case "$1" in
        *headphone*|*headset*) echo "headphones" ;;
        *analog-stereo*)       echo "speakers" ;;
        *)                     echo "unknown" ;;
    esac
}

# Visual indication of sink change
notify_sink() {
    local type="$1"
    case "$type" in
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

# Fading out LEDs
fade_out() {
    for _ in {1..3}; do
        inputmodule-control led-matrix --test off >/dev/null 2>&1
        sleep 0.05
    done
}

# Short pause before EQ resumes
fade_in() {
    inputmodule-control led-matrix --test off >/dev/null 2>&1
    sleep 0.05
}

# Start EQ or fallback
start_eq() {
    if pactl_ok; then
        $EQ_CMD &
        EQ_PID=$!
    else
        start_fallback
    fi
}

start_fallback() {
    inputmodule-control led-matrix --random-eq >/dev/null 2>&1 &
    EQ_PID=$!
}

# Stop EQ process
stop_eq() {
    [[ -n "${EQ_PID:-}" ]] && kill "$EQ_PID" >/dev/null 2>&1 || true
    wait "${EQ_PID:-}" 2>/dev/null || true
}

# Cleanup on exit
cleanup() {
    log "Restoring original input source: $ORIG_SOURCE"
    stop_eq

    if pactl_ok; then
        pactl set-default-source "$ORIG_SOURCE" >/dev/null 2>&1 || true
    fi

    [[ -n "${SUB_PID:-}" ]] && kill "$SUB_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# ---------------- STARTUP -----------------
ORIG_SOURCE=$(pactl info | sed -n 's/^Default Source: //p')
[[ -z "$ORIG_SOURCE" ]] && { log "No default source found"; exit 1; }
log "Original input source: $ORIG_SOURCE"

CURRENT_SINK="$(get_default_sink)"
MONITOR="$(monitor_name_for_sink "$CURRENT_SINK")"

set_default_source "$MONITOR"
start_eq

# ---------------- MAIN LOOP ----------------
pactl subscribe | while read -r line; do
    case "$line" in
        *"on server"*|*"on sink"*)
            NEW_SINK="$(get_default_sink)"
            if [[ "$NEW_SINK" != "$CURRENT_SINK" && -n "$NEW_SINK" ]]; then
                log "🔄 Sink change detected → $NEW_SINK"

                stop_eq

                SINK_TYPE="$(sink_type "$NEW_SINK")"

                fade_out
                notify_sink "$SINK_TYPE"
                fade_in

                MONITOR="$(monitor_name_for_sink "$NEW_SINK")"
                log "→ Input now follows: $MONITOR"
                set_default_source "$MONITOR"

                # ✅ Avoid exiting due to set -e if monitor is slow
                if ! wait_for_monitor_running "$MONITOR"; then
                    log "⚠ Monitor never reached RUNNING/IDLE, using fallback"
                    start_fallback
                else
                    start_eq
                fi

                CURRENT_SINK="$NEW_SINK"
            fi
            ;;
    esac
done &
SUB_PID=$!

wait "$SUB_PID"
