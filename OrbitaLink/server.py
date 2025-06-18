from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
from datetime import datetime
from pydantic import BaseModel, ValidationError, Field
import requests
import os
import random
from flask import jsonify

app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")
API_KEY = "2ec61f431b6e20db0262d465508aa20c2bd90e11"

# In-memory client storage
client_data_map = {}

from typing import Optional
from uuid import uuid4


class Satellite(BaseModel):
    id: Optional[int] = None
    name: str
    tle1: Optional[str] = "N/A"
    tle2: Optional[str] = "N/A"


# -------------------- 🌐 External Data --------------------


@app.route("/api/satellite/<int:norad_id>")
def get_satellite_by_norad(norad_id):
    try:
        url = f"https://db.satnogs.org/api/satellites/?norad_cat_id={norad_id}"
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return (
                jsonify({"error": f"SatNOGS API returned {response.status_code}"}),
                502,
            )

        data = response.json()

        if not data:
            return jsonify({"error": "No satellite found for given NORAD ID"}), 404

        return jsonify(data[0])  # Return first matching satellite
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


def fetch_satellites():
    headers = {"Authorization": f"Token {API_KEY}"}
    try:
        response = requests.get(
            "https://db.satnogs.org/api/satellites/", headers=headers
        )
        if response.status_code == 200:
            raw_data = response.json()
            valid_satellites = []
            for item in raw_data[:20]:  # You can adjust the limit
                try:
                    # Assign fallback id if not present
                    if "id" not in item:
                        item["id"] = abs(hash(item.get("sat_id", str(uuid4())))) % (
                            10**6
                        )

                    sat = Satellite(**item)
                    valid_satellites.append(sat)
                except ValidationError as e:
                    print(
                        f"⚠️ Validation Error for satellite: {item.get('name', 'Unknown')} -",
                        e.errors()[0]["msg"],
                    )
            return valid_satellites
    except Exception as e:
        print("[SATELLITE FETCH ERROR]", e)
    return []


def convert_satellite_to_client_format(sat: Satellite):
    return {
        "name": sat.name,
        "ip": f"192.168.0.{random.randint(1, 255)}",
        "lat": f"{round(random.uniform(-90, 90), 2)}°N",
        "lon": f"{round(random.uniform(-180, 180), 2)}°E",
        "tle_line1": sat.tle1,
        "tle_line2": sat.tle2,
        "az": round(random.uniform(0, 360), 2),
        "el": round(random.uniform(0, 90), 2),
        "time": datetime.now().strftime("%I:%M:%S %p IST"),
        "temp": round(random.uniform(20, 35), 1),
        "humidity": round(random.uniform(40, 80), 1),
    }


# -------------------- 📡 Socket Events --------------------
@socketio.on("connect")
def handle_connect():
    log_msg = (
        f"[{datetime.now().strftime('%H:%M:%S')}] Dashboard connected: {request.sid}"
    )
    print(log_msg)
    emit("log", log_msg)


@socketio.on("client_data")
def handle_client_data(data):
    client_id = data.get("client_ip", request.sid)
    client_data_map[client_id] = data

    # Broadcast updated data to all dashboards
    socketio.emit("client_data_update", {"clients": list(client_data_map.values())})

    log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] Data received from {client_id}"
    print(log_msg)
    socketio.emit("log", log_msg)


@socketio.on("get_satellite_list")
def send_satellite_list():
    sats = fetch_satellites()
    dropdown_data = [{"id": sat.id, "name": sat.name} for sat in sats]
    emit("satellite_list", dropdown_data)


@socketio.on("get_satellite_data")
def send_selected_satellite_data(sat_id):
    sats = fetch_satellites()
    selected = next((s for s in sats if s.id == int(sat_id)), None)
    if selected:
        formatted = convert_satellite_to_client_format(selected)
        emit("client_data_update", {"clients": [formatted]})
        emit("log", f"Fetched data for: {formatted['name']}")
    else:
        emit("log", f"No satellite found with ID {sat_id}")


# -------------------- 🧩 Static Routes --------------------


@app.route("/api/satellites")
def get_all_satellites():
    satellites = fetch_satellites()
    return jsonify([s.model_dump() for s in satellites])


@app.route("/select")
def satellite_selector():
    return app.send_static_file("select.html")


@app.route("/api/norad-list")
def get_norad_list():
    try:
        response = requests.get(
            "https://db.satnogs.org/api/satellites/",
            headers={"User-Agent": "Mozilla/5.0"},
            params={"format": "json", "ordering": "-norad_cat_id", "limit": 50},
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return send_from_directory(".", "dashboard.html")


@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(app.static_folder, "js"), filename)


@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(app.static_folder, "css"), filename)


# -------------------- 🚀 Run --------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
    app.run(debug=True)
