import socketio
import time
import requests
import os
from flask import request

from flask import Flask
from flask_socketio import SocketIO

# === Flask App Config ===
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

SERVER_NAME = os.getenv("SERVER_NAME", "Server 2")
MAIN_SERVER_URL = os.getenv("MAIN_SERVER_URL", "http://localhost:5000")


# === Register with Main Server ===
def register_with_main_server():
    try:
        res = requests.post(
            f"{MAIN_SERVER_URL}/register_activity",
            json={"client": None, "server": SERVER_NAME},
        )
        if res.status_code == 200:
            print(f"[✓] Server '{SERVER_NAME}' registered with main server.")
        else:
            print(f"[!] Failed to register server. Status: {res.status_code}")
    except Exception as e:
        print(f"[x] Error registering server: {e}")


# === Handle Connected Client ===
@socketio.on("register_client")
def handle_client(data):
    client_name = data.get("name", f"Client-{request.sid[:5]}")
    print(f"{client_name} connected to {SERVER_NAME}")

    try:
        requests.post(
            f"{MAIN_SERVER_URL}/register_activity",
            json={"client": client_name, "server": SERVER_NAME},
        )
    except requests.RequestException as e:
        print("Error notifying main server:", e)


@socketio.on("disconnect")
def disconnect():
    print("Client disconnected")


if __name__ == "__main__":
    register_with_main_server()  # 🟢 Register on startup
    socketio.run(app, host="0.0.0.0", port=5002)
