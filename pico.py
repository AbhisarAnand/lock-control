import network
import websocket
import json
import time
import signal
import sys
import os
from machine import Pin, reset

CONFIG_FILE = "config.json"
ws = None 
led = Pin("LED", Pin.OUT)

# Retrieve the actual MAC address of Pico W
def get_mac_address():
    wlan = network.WLAN(network.STA_IF)  # Use station mode
    wlan.active(True)  # Ensure Wi-Fi is active
    mac = wlan.config("mac")  # Get MAC address as bytes
    return ":".join(["{:02X}".format(b) for b in mac])  # Convert to readable format

MAC_ADDRESS = get_mac_address()  # Get MAC at startup
print(f"Pico W MAC Address: {MAC_ADDRESS}")

# Gracefully handle program exit (Ctrl+C)
def handle_exit(signal_received, frame):
    global ws
    print("\nReceived Exit Signal (Ctrl+C). Disconnecting WebSocket...")
    if ws:
        ws.close()
    sys.exit(0)

# Set up signal handling for Ctrl+C
signal.signal(signal.SIGINT, handle_exit)

# Read configuration from config.json
def read_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)
                return config
        except json.JSONDecodeError:
            print("Error: Invalid config.json.")
    return None

# Connect to Wi-Fi
def connect_to_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to Wi-Fi SSID: {ssid}")
        led.on()  # Turn on LED during connection attempt
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            time.sleep(1)
        led.off()  # Turn off LED after successful connection
    print(f"Connected to Wi-Fi. IP Address: {wlan.ifconfig()[0]}")

# Monitor Wi-Fi connection and reconnect if necessary
def monitor_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    while True:
        if not wlan.isconnected():
            print("Wi-Fi connection lost. Attempting to reconnect...")
            connect_to_wifi(ssid, password)
        time.sleep(10)

# Connect to WebSocket Server
def connect_to_websocket(ws_url):
    global ws
    print(f"Connecting to WebSocket Server: {ws_url}")
    led.on()  # Turn on LED during WebSocket connection attempt
    try:
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.on_open = on_open
        ws.run_forever()
    except Exception as e:
        print(f"WebSocket Connection Failed: {e}, retrying in 5s...")
        time.sleep(5)
    led.off()  # Turn off LED after WebSocket connection attempt

# Handle messages from the server
def on_message(ws, message):
    print(f"Raw Message Received: {message}")
    try:
        data = json.loads(message)

        # Respond with MAC Address if requested
        if data.get("request") == "SEND_MAC":
            ws.send(json.dumps({"macAddress": MAC_ADDRESS}))

        # Respond to a heartbeat check (PING)
        if data.get("request") == "PING":
            ws.send(json.dumps({"macAddress": MAC_ADDRESS, "response": "PONG"}))
            print("Sent PONG (I'm Alive)")

        # Handle LOCK/UNLOCK commands
        if data.get("command"):
            print(f"Parsed Command: {data['command']} for MAC: {data['macAddress']}")
            if data["command"] == "LOCK":
                print("Locking the door...")
                led.on()  # Turn on LED to indicate LOCK command
            elif data["command"] == "UNLOCK":
                print("Unlocking the door...")
                led.off()  # Turn off LED to indicate UNLOCK command

        # Handle DISCONNECT message
        if data.get("command") == "DISCONNECT":
            print("Received DISCONNECT command. Closing WebSocket connection...")
            ws.close()
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)  # Delete config.json to prevent reconnection
                print("Deleted config.json. Waiting for new configuration...")
            reset()  # Reset the Pico to enter provisioning state

    except json.JSONDecodeError:
        print("Error: Received non-JSON message")

def on_error(ws, error):
    print(f"WebSocket Error: {error}")

def on_close(ws, close_status, message):
    print("WebSocket Disconnected.")

def on_open(ws):
    print("Connected to Meteor WebSocket Server")
    ws.send(json.dumps({"macAddress": MAC_ADDRESS}))

# Main function
def main():
    config = read_config()
    if config:
        ssid = config.get("ssid")
        password = config.get("password")
        ws_url = config.get("websocket_url", "ws://localhost:8080")
        if ssid and password:
            connect_to_wifi(ssid, password)
            # Start Wi-Fi monitoring in a separate thread
            import _thread
            _thread.start_new_thread(monitor_wifi, (ssid, password))
            # Connect to WebSocket
            connect_to_websocket(ws_url)
        else:
            print("Error: Wi-Fi credentials not found in config.json.")
    else:
        print("Error: config.json not found.")

if __name__ == "__main__":
    main()
