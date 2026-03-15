# Pico 2W REST-Controlled USB Keyboard Emulator

Author: Generated Guide\
Purpose: Control a restricted PC via USB keyboard using REST API
commands from another computer.\
Hardware: Raspberry Pi Pico 2W (RP2350)

------------------------------------------------------------------------

# 1. Overview

This project builds a **Wi‑Fi controlled USB keyboard emulator** using a
**Raspberry Pi Pico 2W** (RP2350-based).

The Pico 2W connects to:

-   **Restricted PC via USB** (appears as a normal keyboard)
-   **MacBook via Wi‑Fi** (REST API commands)

The restricted PC does **not need any software installed**.

It only sees a **standard USB keyboard**.

------------------------------------------------------------------------

# 2. High-Level Architecture

    MacBook
       │
       │ REST API over Wi‑Fi
       ▼
    Raspberry Pi Pico 2W
       ├─ Wi‑Fi HTTP server
       ├─ command parser
       └─ USB HID keyboard
              │
              │ USB
              ▼
    Restricted PC
    (sees normal keyboard)

Flow:

    REST request → Pico 2W → HID key events → Restricted PC

Example:

    POST /type
    {"text":"hello"}

Results in the PC receiving:

    hello

------------------------------------------------------------------------

# 3. Why There Is No SD Card

The Pico 2W is **not a Raspberry Pi computer**.

It is a **microcontroller board**.

Therefore:

-   No Linux OS
-   No SD card
-   No large storage

Instead it uses **on‑board flash memory**.

Hardware specs (Pico 2W / RP2350):

  Component       Value
  --------------- ------------------------------------
  CPU             RP2350 dual-core Arm Cortex-M33 @ 150 MHz
  Architecture    Selectable Arm Cortex-M33 or Hazard3 RISC-V
  RAM             520 KB on-chip SRAM
  Flash storage   4 MB
  Wi‑Fi           2.4 GHz 802.11b/g/n (Infineon CYW43439)
  Bluetooth       5.2
  Security        Arm TrustZone, signed boot, hardware TRNG
  GPIO            26 multifunctional pins (3 ADC-capable)
  PIO             12 state machines

Your program and files live inside the **4 MB flash chip**.

------------------------------------------------------------------------

# 4. Where the "Operating System" Lives

There are three layers:

## Layer 1 --- Boot ROM

Built into the RP2350 chip.

Responsibilities:

-   USB bootloader
-   firmware flashing

## Layer 2 --- Firmware (CircuitPython)

Installed into flash memory.

Provides:

-   Python runtime
-   Wi‑Fi stack
-   filesystem
-   USB HID support

CircuitPython acts like a **tiny OS runtime**.

## Layer 3 --- Your Application

Files stored on flash:

    CIRCUITPY/
      boot.py
      code.py
      settings.toml
      lib/

`code.py` runs automatically when the Pico boots.

------------------------------------------------------------------------

# 5. Where the REST Server Runs

Your REST server runs inside `code.py`.

Boot process:

    Power On
       ↓
    RP2350 Boot ROM
       ↓
    CircuitPython firmware
       ↓
    boot.py executes
       ↓
    code.py executes
       ↓
    Wi‑Fi server starts

Your Python code listens for HTTP requests.

------------------------------------------------------------------------

# 6. Hardware Required

Minimum components:

  Item                   Purpose
  ---------------------- -------------------------------
  Raspberry Pi Pico 2W   microcontroller + Wi‑Fi + BLE
  USB cable             connect Pico to restricted PC
  MacBook               REST client

Optional:

  Item                  Purpose
  --------------------- ------------------
  USB extension cable   easier placement
  enclosure             protection
  small router          isolated network

------------------------------------------------------------------------

# 7. Connection Diagram

    MacBook
      │
      │ Wi‑Fi
      ▼
    Pico 2W
      │
      │ USB cable
      ▼
    Restricted PC

Important detail:

The **USB cable connects Pico → Restricted PC**, not the Mac.

------------------------------------------------------------------------

# 8. Software Stack

Recommended stack:

  Layer             Technology
  ----------------- ---------------------------
  Firmware          CircuitPython 10.x
  Networking        Wi‑Fi (via settings.toml)
  Web API           adafruit_httpserver
  Keyboard output   USB HID

Libraries used:

-   usb_hid (built-in)
-   adafruit_hid
-   adafruit_httpserver
-   wifi / socketpool (built-in)

------------------------------------------------------------------------

# 9. Flashing CircuitPython

Steps:

1.  Hold **BOOTSEL** on Pico 2W
2.  Plug into Mac
3.  Device appears as **RP2350** (not RPI-RP2 like the older Pico W)
4.  Download CircuitPython 10.x `.uf2` for Pico 2W from:
    https://circuitpython.org/board/raspberry_pi_pico2_w/
5.  Copy the `.uf2` file to the RP2350 drive
6.  Pico reboots automatically

Now a new drive appears:

    CIRCUITPY

Also download the CircuitPython 10.x library bundle from:
https://circuitpython.org/libraries

Copy these folders into `CIRCUITPY/lib/`:

-   `adafruit_hid/`
-   `adafruit_httpserver/`

------------------------------------------------------------------------

# 10. Configure USB Keyboard Mode

Create `boot.py`:

``` python
import usb_hid
import usb_cdc
import usb_midi
import storage

usb_cdc.disable()
usb_midi.disable()
storage.disable_usb_drive()

usb_hid.enable(
    (usb_hid.Device.KEYBOARD,),
    boot_device=1
)
```

This makes the device appear **only as a keyboard**.

Note: disabling USB storage means you cannot edit files via the
CIRCUITPY drive while this boot.py is active. To regain file access,
hold BOOTSEL and re-flash, or add a GPIO-based safety switch to
conditionally skip the disables.

------------------------------------------------------------------------

# 10.5. Configure Wi‑Fi Credentials (settings.toml)

Create `settings.toml` on the CIRCUITPY drive:

``` toml
CIRCUITPY_WIFI_SSID = "YourNetworkName"
CIRCUITPY_WIFI_PASSWORD = "YourPassword"
```

CircuitPython reads these automatically. Your code accesses them
via `os.getenv()`. This keeps credentials out of your code.

------------------------------------------------------------------------

# 11. Example REST Server (code.py)

``` python
import os
import wifi
import socketpool
import usb_hid

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_httpserver import Server, Request, Response, POST

# --- USB HID keyboard setup ---
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

# --- Wi‑Fi connection ---
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"),
    os.getenv("CIRCUITPY_WIFI_PASSWORD"),
)
print(f"Connected to Wi‑Fi. IP: {wifi.radio.ipv4_address}")

# --- HTTP server ---
pool = socketpool.SocketPool(wifi.radio)
server = Server(pool)

@server.route("/type", POST)
def handle_type(request: Request):
    """Type a string as keyboard input."""
    import json
    body = json.loads(request.body)
    text = body.get("text", "")
    layout.write(text)
    return Response(request, "OK")

@server.route("/keypress", POST)
def handle_keypress(request: Request):
    """Press a single key by name (e.g. ENTER, TAB, ESCAPE)."""
    import json
    body = json.loads(request.body)
    key_name = body.get("key", "").upper()
    keycode = getattr(Keycode, key_name, None)
    if keycode is not None:
        kbd.send(keycode)
        return Response(request, "OK")
    return Response(request, f"Unknown key: {key_name}", status=(400, "Bad Request"))

@server.route("/")
def handle_root(request: Request):
    """Health check."""
    return Response(request, "Pico 2W Keyboard Ready")

server.serve_forever(str(wifi.radio.ipv4_address), port=80)
```

------------------------------------------------------------------------

# 12. Example REST Calls

Type text:

    curl -X POST http://device-ip/type \
         -d '{"text":"hello"}'

Press key:

    curl -X POST http://device-ip/keypress \
         -d '{"key":"ENTER"}'

------------------------------------------------------------------------

# 13. Development Workflow

During development:

    MacBook ─USB─ Pico

Edit files on `CIRCUITPY`.

Once ready:

    MacBook → Wi‑Fi → Pico
    Pico → USB → Restricted PC

------------------------------------------------------------------------

# 14. Security Recommendations

Since this exposes a REST API:

-   Require API token
-   Restrict to local network
-   Avoid internet exposure

------------------------------------------------------------------------

# 15. Performance

Typical latency:

    REST request → keypress
    ≈ 10–50 ms

This is effectively instant typing.

------------------------------------------------------------------------

# 16. Troubleshooting

  Problem                       Fix
  ----------------------------- ------------------------
  PC does not detect keyboard   verify USB HID enabled
  Wi‑Fi fails                   check credentials
  REST endpoint unreachable     confirm IP address
  keys stuck                    add key release logic

------------------------------------------------------------------------

# 17. Optional Improvements

Possible upgrades:

-   API authentication
-   command queue
-   macro scripts
-   OTA firmware updates
-   keyboard passthrough

------------------------------------------------------------------------

# 18. Summary

The Pico 2W provides a **very compact architecture**:

-   Wi‑Fi control
-   USB keyboard emulation
-   REST API interface
-   No software on target PC
-   No SD card required

The entire system fits on a **~$7 microcontroller board**.
