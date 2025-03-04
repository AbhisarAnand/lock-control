import websocket
import json
import time
import signal
import sys
import os
import network

CONFIG_FILE = "config.json"  # Config file to store WebSocket URL
ws = None  # Global WebSocket variable


# ✅ Retrieve the actual MAC address of PicoW
def get_mac_address():
    wlan = network.WLAN(network.STA_IF)  # Use station mode
    wlan.active(True)  # Ensure Wi-Fi is active
    mac = wlan.config("mac")  # Get MAC address as bytes
    return ":".join(["{:02X}".format(b) for b in mac])  # Convert to readable format


MAC_ADDRESS = get_mac_address()  # Get MAC at startup
print(f"📡 PicoW MAC Address: {MAC_ADDRESS}")


# Gracefully handle program exit (Ctrl+C)
def handle_exit(signal_received, frame):
    global ws
    print("\n❌ Received Exit Signal (Ctrl+C). Disconnecting WebSocket...")
    if ws:
        ws.close()
    sys.exit(0)


# Set up signal handling for Ctrl+C
signal.signal(signal.SIGINT, handle_exit)


# Read WebSocket URL from config.json
def get_websocket_url():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)
                return config.get("websocket_url", "ws://localhost:8080")
        except json.JSONDecodeError:
            print("❌ Error: Invalid config.json, using default WebSocket URL.")
    return "ws://localhost:8080"


# Connect to WebSocket Server
def connect():
    global ws
    while True:
        ws_url = get_websocket_url()
        print(f"🔗 Connecting to WebSocket Server: {ws_url}")
        
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
            print(f"❌ WebSocket Connection Failed: {e}, retrying in 5s...")
            time.sleep(5)


# Handle messages from the server
def on_message(ws, message):
    print(f"📩 Raw Message Received: {message}")
    try:
        data = json.loads(message)

        # Respond with MAC Address if requested
        if data.get("request") == "SEND_MAC":
            ws.send(json.dumps({"macAddress": MAC_ADDRESS}))

        # Respond to a heartbeat check (PING)
        if data.get("request") == "PING":
            ws.send(json.dumps({"macAddress": MAC_ADDRESS, "response": "PONG"}))
            print("✅ Sent PONG (I'm Alive)")

        # Handle LOCK/UNLOCK commands
        if data.get("command"):
            print(f"📩 Parsed Command: {data['command']} for MAC: {data['macAddress']}")
            if data["command"] == "LOCK":
                print("🔒 Locking the door...")
            elif data["command"] == "UNLOCK":
                print("🔓 Unlocking the door...")

        # Handle DISCONNECT message
        if data.get("command") == "DISCONNECT":
            print("❌ Received DISCONNECT command. Closing WebSocket connection...")
            ws.close()
            os.remove(CONFIG_FILE)  # Delete config.json to prevent reconnection
            print("🗑️ Deleted config.json. Waiting for new configuration...")
            wait_for_config()  # Enter wait mode
    except json.JSONDecodeError:
        print("❌ Error: Received non-JSON message")


# Wait for config.json to reappear before reconnecting
def wait_for_config():
    while not os.path.exists(CONFIG_FILE):
        print("🔍 Waiting for new config.json...")
        time.sleep(5)
    print("✅ New config.json detected! Reconnecting...")
    connect()


def on_error(ws, error):
    print(f"❌ WebSocket Error: {error}")


def on_close(ws, close_status, message):
    print("❌ WebSocket Disconnected.")
    wait_for_config()  # Wait for new config.json before reconnecting


def on_open(ws):
    print("✅ Connected to Meteor WebSocket Server")
    ws.send(json.dumps({"macAddress": MAC_ADDRESS}))


# Start WebSocket Client
connect()
