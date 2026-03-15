"""
GhostType - boot.py
Configures the Pico 2W to appear as a USB keyboard only.

WARNING: This disables the CIRCUITPY USB drive and serial console.
To regain file access, hold BOOTSEL and re-flash CircuitPython.
"""

import usb_hid
import usb_cdc
import usb_midi
import storage

# Disable USB drive, serial console, and MIDI to free endpoints
usb_cdc.disable()
usb_midi.disable()
storage.disable_usb_drive()

# Enable only the keyboard HID device
usb_hid.enable(
    (usb_hid.Device.KEYBOARD,),
    boot_device=1,
)
