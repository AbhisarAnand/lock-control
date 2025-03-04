import os
import time
import json
import shutil
import subprocess
from pathlib import Path

# Configuration
WEBSOCKET_URL = "ws://raspberrypi:8080"  # Update with actual Meteor WebSocket URL
PICO_MOUNT_PATH = "/media/pi/RPI-RP2"  # Default mount point for PicoW on Raspberry Pi
CONFIG_FILE = "config.json"
FIRMWARE_FILE = "pico_firmware.uf2"  # Firmware file to flash on the PicoW
CHECK_INTERVAL = 5  # Time (seconds) between checking for new devices

def detect_pico():
    """ Continuously check for a PicoW connection. """
    while True:
        if Path(PICO_MOUNT_PATH).exists():
            print("✅ PicoW detected!")
            return True
        time.sleep(CHECK_INTERVAL)  # Wait before checking again

def provision_pico():
    """ Provision the PicoW: Add config and firmware. """
    if not Path(PICO_MOUNT_PATH).exists():
        print("❌ Error: PicoW disconnected before provisioning!")
        return False

    # Create config.json with WebSocket URL
    config_data = {"websocket_url": WEBSOCKET_URL}
    config_path = Path(PICO_MOUNT_PATH) / CONFIG_FILE
    with open(config_path, "w") as config_file:
        json.dump(config_data, config_file, indent=4)

    print(f"📂 {CONFIG_FILE} added with WebSocket URL.")

    # Copy firmware if available
    firmware_path = Path(FIRMWARE_FILE)
    if firmware_path.exists():
        shutil.copy(firmware_path, PICO_MOUNT_PATH)
        print(f"🚀 {FIRMWARE_FILE} flashed onto PicoW.")

    return True

def eject_pico():
    """ Eject the PicoW after provisioning. """
    print("🔄 Ejecting PicoW...")
    try:
        subprocess.run(["sync"], check=True)  # Ensure all writes are completed
        subprocess.run(["udisksctl", "unmount", "-b", "/dev/sda1"], check=True)
        print("✅ PicoW safely ejected!")
    except subprocess.CalledProcessError:
        print("⚠️ Failed to eject PicoW, but provisioning is done.")

def main():
    print("🚀 Starting PicoW Auto-Provisioning Script (Running 24/7)...")
    while True:  # Infinite loop to keep running
        print("🔍 Waiting for a PicoW...")
        detect_pico()
        if provision_pico():
            eject_pico()
        print("♻️ Restarting detection loop...")  
        time.sleep(CHECK_INTERVAL)  # Small delay before next check

if __name__ == "__main__":
    main()
