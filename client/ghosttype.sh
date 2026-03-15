#!/usr/bin/env bash
#
# GhostType CLI - Send keystrokes to your Pico 2W over Wi-Fi
#
# Usage:
#   ghosttype type "hello world"
#   ghosttype key ENTER
#   ghosttype combo CONTROL C
#   ghosttype status

set -euo pipefail

HOST="${GHOSTTYPE_HOST:-pico-kbd.local}"
PORT="${GHOSTTYPE_PORT:-80}"
BASE="http://${HOST}:${PORT}"

usage() {
    echo "GhostType CLI"
    echo ""
    echo "Usage:"
    echo "  ghosttype type <text>        Type a string"
    echo "  ghosttype key <KEY>          Press a single key (ENTER, TAB, ESCAPE, ...)"
    echo "  ghosttype combo <KEY> ...    Press a key combination (CONTROL C, ALT TAB, ...)"
    echo "  ghosttype status             Check if GhostType is reachable"
    echo ""
    echo "Environment:"
    echo "  GHOSTTYPE_HOST  Hostname or IP (default: pico-kbd.local)"
    echo "  GHOSTTYPE_PORT  Port (default: 80)"
    echo ""
    echo "Key names: ENTER, TAB, ESCAPE, BACKSPACE, DELETE, SPACE,"
    echo "  UP_ARROW, DOWN_ARROW, LEFT_ARROW, RIGHT_ARROW,"
    echo "  CONTROL, SHIFT, ALT, GUI (Windows/Cmd key),"
    echo "  F1-F12, A-Z, ONE-ZERO, etc."
    echo ""
    echo "Examples:"
    echo "  ghosttype type 'Hello World'"
    echo "  ghosttype key ENTER"
    echo "  ghosttype combo CONTROL A"
    echo "  ghosttype combo ALT F4"
    exit 1
}

cmd_type() {
    local text="$*"
    curl -s -X POST "${BASE}/type" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"${text}\"}"
    echo ""
}

cmd_key() {
    local key="$1"
    curl -s -X POST "${BASE}/keypress" \
        -H "Content-Type: application/json" \
        -d "{\"key\":\"${key}\"}"
    echo ""
}

cmd_combo() {
    local json_keys=""
    for k in "$@"; do
        if [ -n "$json_keys" ]; then
            json_keys="${json_keys},"
        fi
        json_keys="${json_keys}\"${k}\""
    done
    curl -s -X POST "${BASE}/combo" \
        -H "Content-Type: application/json" \
        -d "{\"keys\":[${json_keys}]}"
    echo ""
}

cmd_status() {
    echo "Checking ${BASE} ..."
    curl -s --max-time 5 "${BASE}/" && echo "" || echo "GhostType is not reachable at ${BASE}"
}

[ $# -lt 1 ] && usage

case "$1" in
    type)
        shift
        [ $# -lt 1 ] && { echo "Error: missing text"; exit 1; }
        cmd_type "$@"
        ;;
    key)
        shift
        [ $# -ne 1 ] && { echo "Error: specify exactly one key"; exit 1; }
        cmd_key "$1"
        ;;
    combo)
        shift
        [ $# -lt 2 ] && { echo "Error: specify at least two keys"; exit 1; }
        cmd_combo "$@"
        ;;
    status)
        cmd_status
        ;;
    *)
        usage
        ;;
esac
