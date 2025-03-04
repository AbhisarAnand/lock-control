import os
import time
import json
import shutil
import subprocess
import getpass
import socket
from pathlib import Path

# Configuration
PICO_MOUNT_PATH = f"/media/{getpass.getuser()}/RPI-RP2"  # Detects current user
CONFIG_FILE = "config.json"
FIRMWARE_FILE = "pico_firmware.uf2"  # Firmware file for PicoW
PICO_SCRIPT = "pico.py"  # Script to run on Pico
PICO_RUN_SCRIPT = "main.py"  # Rename it so it runs on startup
CHECK_INTERVAL = 5  # Time (seconds) between checking for new devices

# Wi-Fi Credentials
SSID = "YourWiFiSSID"
PASSWORD = "YourWiFiPassword"

def get_raspberry_pi_ip():
    """ Detect the Raspberry Pi's local network IP address dynamically. """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to an external server to determine local IP
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Error detecting Raspberry Pi IP: {e}")
        return "raspberrypi"  # Fallback to hostname if IP detection fails

def detect_pico():
    """ Continuously check for a PicoW connection. """
    while True:
        if Path(PICO_MOUNT_PATH).exists():
            print("PicoW detected!")
            return True
        time.sleep(CHECK_INTERVAL)  # Wait before checking again

def provision_pico():
    """ Provision the PicoW: Add config, Wi-Fi credentials, and firmware. """
    if not Path(PICO_MOUNT_PATH).exists():
        print("Error: PicoW disconnected before provisioning!")
        return False

    # Get dynamic WebSocket URL
    websocket_url = f"ws://{get_raspberry_pi_ip()}:8080"

    # Create config.json with WebSocket URL and Wi-Fi credentials
    config_data = {
        "websocket_url": websocket_url,
        "wifi": {
            "ssid": SSID,
            "password": PASSWORD
        }
    }
    
    config_path = Path(PICO_MOUNT_PATH) / CONFIG_FILE
    with open(config_path, "w") as config_file:
        json.dump(config_data, config_file, indent=4)

    print(f"{CONFIG_FILE} added with WebSocket URL: {websocket_url}")

    # Copy firmware if available
    firmware_path = Path(FIRMWARE_FILE)
    if firmware_path.exists():
        shutil.copy(firmware_path, PICO_MOUNT_PATH)
        print(f"Flashed {FIRMWARE_FILE} onto PicoW.")

    # Copy the script and rename it for auto-run
    script_src = Path(PICO_SCRIPT)
    script_dest = Path(PICO_MOUNT_PATH) / PICO_RUN_SCRIPT
    if script_src.exists():
        shutil.copy(script_src, script_dest)
        print(f"Copied {PICO_SCRIPT} as {PICO_RUN_SCRIPT} for auto-start.")

    return True

def eject_pico():
    """ Eject the PicoW after provisioning safely. """
    print("Ejecting PicoW...")

    try:
        # Ensure all writes are fully committed
        subprocess.run(["sync"], check=True)

        # Properly unmount the Pico
        unmount_result = subprocess.run(["udisksctl", "unmount", "-b", "/dev/sda1"], capture_output=True, text=True)

        if unmount_result.returncode == 0:
            print("PicoW successfully unmounted.")

            # Eject the Pico to ensure a clean removal
            eject_result = subprocess.run(["udisksctl", "power-off", "-b", "/dev/sda1"], capture_output=True, text=True)

            if eject_result.returncode == 0:
                print("PicoW safely ejected!")
            else:
                print(f"Warning: Failed to fully power off the Pico. {eject_result.stderr}")
        else:
            print(f"Warning: Unmount failed, but proceeding. {unmount_result.stderr}")

    except subprocess.CalledProcessError as e:
        print(f"Error ejecting PicoW: {e}")

    # Add a delay to ensure it fully powers off before unplugging
    time.sleep(2)

def main():
    print("Starting PicoW Auto-Provisioning Script (Running 24/7)...")
    while True:  # Infinite loop to keep running
        print("Waiting for a PicoW...")
        detect_pico()
        if provision_pico():
            eject_pico()
        print("Restarting detection loop...")  
        time.sleep(CHECK_INTERVAL)  # Small delay before next check

if __name__ == "__main__":
    main()
