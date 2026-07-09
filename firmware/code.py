"""
GhostType - Wi-Fi controlled USB keyboard emulator
Main application: REST API server for sending keystrokes over HTTP.

Runs on Raspberry Pi Pico 2W with CircuitPython.
"""

import os
import board
import digitalio
import wifi
import socketpool
import mdns
import usb_hid
import json
import time

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_httpserver import Server, Request, Response, POST

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

# --- USB HID keyboard setup ---
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# --- Wi-Fi connection (must happen before LED setup on Pico 2W) ---
ssid = os.getenv("CIRCUITPY_WIFI_SSID")
print("Connecting to Wi-Fi: " + ssid)
wifi.radio.connect(ssid, os.getenv("CIRCUITPY_WIFI_PASSWORD"))
# Keep the radio always-on (set after connect, which can reset it):
# power-save mode drops multicast frames, making mDNS (pico-kbd.local)
# resolution unreliable.
wifi.radio.power_management = wifi.PowerManagement.NONE
ip = str(wifi.radio.ipv4_address)
print("Connected! IP: " + ip)

# --- Onboard LED setup (after Wi-Fi, since LED is on the CYW43439 chip) ---
led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT
led.value = False

LED_FLASH_DURATION = 0.05  # seconds


def flash_led():
    """Briefly flash the onboard LED to indicate a keystroke."""
    led.value = True
    time.sleep(LED_FLASH_DURATION)
    led.value = False

# --- mDNS ---
# Hostname is configurable via settings.toml (MDNS_HOSTNAME) so multiple
# keyboards can share this firmware without colliding on the network.
# Defaults to "pico-kbd" to preserve the original single-device behaviour.
hostname = os.getenv("MDNS_HOSTNAME") or "pico-kbd"
mdns_server = mdns.Server(wifi.radio)
mdns_server.hostname = hostname
mdns_server.advertise_service(service_type="_http", protocol="_tcp", port=80)
print("Reachable at: http://" + hostname + ".local")

# --- HTTP server ---
pool = socketpool.SocketPool(wifi.radio)
server = Server(pool)


def cors_response(request, body="OK", status=None):
    if status:
        return Response(request, body, headers=CORS_HEADERS, status=status)
    return Response(request, body, headers=CORS_HEADERS)


# --- Control page (served over Wi-Fi; the USB side stays keyboard-only) ---
# The page lives on the Pico's flash. boot.py hides the USB drive from the
# host, but CircuitPython can still read its own files to serve them.
try:
    with open("index.html", "r") as f:
        INDEX_HTML = f.read()
except OSError:
    INDEX_HTML = "<h1>GhostType</h1><p>index.html missing on device.</p>"


@server.route("/", ["GET", "OPTIONS"])
def handle_root(request: Request):
    """Serve the browser control page. Open http://<host>/ on any device."""
    if request.method == "OPTIONS":
        return cors_response(request, "")
    return Response(request, INDEX_HTML, content_type="text/html", headers=CORS_HEADERS)


@server.route("/status", ["GET", "OPTIONS"])
def handle_status(request: Request):
    """Plain-text health check used by the control page's status line."""
    if request.method == "OPTIONS":
        return cors_response(request, "")
    return cors_response(request, "GhostType Ready - IP: " + ip)


@server.route("/type", [POST, "OPTIONS"])
def handle_type(request: Request):
    """Type a string as keyboard input."""
    if request.method == "OPTIONS":
        return cors_response(request, "")
    body = json.loads(request.body)
    text = body.get("text", "")
    if text:
        layout.write(text)
        flash_led()
    return cors_response(request, "OK: typed " + str(len(text)) + " chars")


@server.route("/keypress", [POST, "OPTIONS"])
def handle_keypress(request: Request):
    """Press a single key by name (e.g. ENTER, TAB, ESCAPE)."""
    if request.method == "OPTIONS":
        return cors_response(request, "")
    body = json.loads(request.body)
    key_name = body.get("key", "").upper()
    keycode = getattr(Keycode, key_name, None)
    if keycode is not None:
        kbd.send(keycode)
        flash_led()
        return cors_response(request, "OK: " + key_name)
    return cors_response(request, "Unknown key: " + key_name, status=(400, "Bad Request"))


@server.route("/combo", [POST, "OPTIONS"])
def handle_combo(request: Request):
    """Press a key combination (e.g. Ctrl+C, Alt+Tab)."""
    if request.method == "OPTIONS":
        return cors_response(request, "")
    body = json.loads(request.body)
    keys = body.get("keys", [])
    keycodes = []
    for k in keys:
        kc = getattr(Keycode, k.upper(), None)
        if kc is None:
            return cors_response(request, "Unknown key: " + k, status=(400, "Bad Request"))
        keycodes.append(kc)
    if keycodes:
        kbd.send(*keycodes)
        flash_led()
    return cors_response(request, "OK: combo " + "+".join(keys))


print("GhostType server starting on port 80...")
server.serve_forever(ip, port=80)
