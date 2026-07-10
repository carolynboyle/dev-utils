#!/bin/bash
#
# end_session - Politely close all windows, then force-close stragglers,
# then kill the session manager so xrdp/sesman gives a clean login prompt
# on next connection.
#
# Usage: end_session -w 5
#   -w SECONDS   Wait time per window in pass 1, and grace period before
#                pass 2 begins. Default: 3

LOGFILE="$HOME/.local/share/end_session.log"
mkdir -p "$(dirname "$LOGFILE")"
: > "$LOGFILE"   # truncate/overwrite each run

log() {
    echo "$(date '+%F %T') $1" >> "$LOGFILE"
}

# --- Parse args ---
WAIT=3
while getopts "w:" opt; do
    case $opt in
        w) WAIT="$OPTARG" ;;
        *) echo "Usage: end_session -w SECONDS" ; exit 1 ;;
    esac
done

log "=== end_session started (wait=${WAIT}s) ==="

# --- Check dependencies ---
for cmd in wmctrl xdotool; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log "ERROR: required command '$cmd' not found. Aborting."
        echo "Error: '$cmd' is not installed. See $LOGFILE for details."
        exit 1
    fi
done

# --- Pass 1: ask each window to close, one at a time ---
log "--- Pass 1: polite close requests ---"

# Snapshot: window ID + title
mapfile -t initial_windows < <(wmctrl -l | awk '{print $1}')

log "Found ${#initial_windows[@]} open window(s) at start:"
wmctrl -l >> "$LOGFILE"

for win in "${initial_windows[@]}"; do
    title=$(wmctrl -l | grep "^$win" | cut -d' ' -f5-)
    log "Requesting close: $win ($title)"
    wmctrl -ic "$win"
    sleep "$WAIT"

    if wmctrl -l | grep -q "^$win"; then
        log "Still open after ${WAIT}s: $win ($title)"
    else
        log "Closed successfully: $win ($title)"
    fi
done

log "--- Pass 1 complete ---"

# --- Pass 2: force-close anything still standing ---
log "--- Pass 2: force-close stragglers ---"

mapfile -t remaining_windows < <(wmctrl -l | awk '{print $1}')

if [ "${#remaining_windows[@]}" -eq 0 ]; then
    log "No windows remaining. Pass 2 has nothing to do."
else
    log "Found ${#remaining_windows[@]} window(s) still open:"
    wmctrl -l >> "$LOGFILE"

    for win in "${remaining_windows[@]}"; do
        title=$(wmctrl -l | grep "^$win" | cut -d' ' -f5-)
        pid=$(xdotool getwindowpid "$win" 2>>"$LOGFILE")

        if [ -z "$pid" ]; then
            log "Could not determine PID for window $win ($title). Skipping."
            continue
        fi

        log "Force-killing window $win ($title), PID $pid"
        if kill "$pid" 2>>"$LOGFILE"; then
            log "kill signal sent successfully to PID $pid"
        else
            log "kill FAILED for PID $pid"
        fi
    done
fi

log "--- Pass 2 complete ---"

# --- End session manager ---
log "--- Ending session manager ---"
if pkill -u "$USER" -f "cinnamon-session|xfce4-session|lxsession"; then
    log "Session manager kill signal sent successfully."
else
    log "Session manager kill FAILED or no matching process found."
fi

log "=== end_session finished ==="
