#!/usr/bin/env bash
set -euo pipefail

# ---------------- Config ----------------
BASE_CMD="inputmodule-control led-matrix"
EQ_CMD="$BASE_CMD --input-eq"
FALLBACK_CMD="$BASE_CMD --random-eq"
CHECK_INTERVAL=1
EQ_PID=""
CLEANUP_FLAG=0
FILTER_SINK="led_eq_input"
FILTER_SOURCE="led_eq_output"


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
    pkill -f "${EQ_CMD}" >/dev/null 2>&1 || true

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
            # Show horizontal bar for speakers
            ${BASE_CMD} --pattern all-on >/dev/null 2>&1
            ;;
        headphones)
            # Show vertical bars for headphones
            ${BASE_CMD} --pattern zigzag >/dev/null 2>&1
            ;;
        bluetooth)
            # Unknown source → flash everything briefly
            ${BASE_CMD} --pattern gradient >/dev/null 2>&1
            ;;
        *)
            # Unknown source → flash everything briefly
            ${BASE_CMD} --pattern gradient >/dev/null 2>&1
            ;;
    esac

    # Keep cue visible briefly
    sleep 0.6
}

# wire_filter() {
#     local monitor="$1"

#     log "→ Linking $monitor → led_eq_input"

#     # Remove any existing links to avoid duplicates
#     pw-link -d "$monitor" led_eq_input 2>/dev/null || true

#     # Create the link
#     pw-link "$monitor" led_eq_input

#     # Make the filter output the default source
#     pactl set-default-source led_eq_output
# }
wire_filter() {
    local monitor="$1"

    log "→ Wiring $monitor → led_eq → inputmodule-control"

    # pw-link "${monitor}:monitor_FL" led_eq:input_FL
    # pw-link "${monitor}:monitor_FR" led_eq:input_FR

    pw-link alsa_output.pci-0000_c2_00.6.analog-stereo:monitor_FL led_eq:input_FL
    pw-link alsa_output.pci-0000_c2_00.6.analog-stereo:monitor_FR led_eq:input_FR

    pactl set-default-source led_eq
}


# ---------------- Cleanup ----------------

cleanup() {
    if [ $CLEANUP_FLAG -eq 1 ]; then return; fi
    CLEANUP_FLAG=1
    log "Restoring original input source: $ORIG_SOURCE"
    stop_eq
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

wire_filter "$MONITOR"

if wait_for_monitor_running "$MONITOR"; then
    log "→ Monitor ready: $MONITOR"
    start_eq
else
    log "⚠ Monitor not ready, using fallback EQ"
    start_fallback
fi

# ---------------- Main Loop ----------------

pactl subscribe | while read -r line; do
    case "$line" in
        *"on server"*|*"on sink"*)
            NEW_SINK="$(current_sink)"
            if [[ "$NEW_SINK" != "$CURRENT_SINK" && -n "$NEW_SINK" ]]; then
                log "🔄 Sink change detected → $NEW_SINK"

                stop_eq

                SINK_TYPE=$(sink_type "$NEW_SINK")
                fade_out
                visual_cue "$SINK_TYPE"
                fade_in

                MONITOR="$(monitor_name_for_sink "$NEW_SINK")"
                log "→ Input now follows: $MONITOR"
                wire_filter "$MONITOR"

                if wait_for_monitor_running "$MONITOR"; then
                    start_eq
                else
                    log "⚠ Monitor never reached RUNNING/IDLE, using fallback"
                    start_fallback
                fi

                CURRENT_SINK="$NEW_SINK"
            fi
            ;;
    esac
done &
SUB_PID=$!

# Wait for subscription loop
wait "$SUB_PID"
