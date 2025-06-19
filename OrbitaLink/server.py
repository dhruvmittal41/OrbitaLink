from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
from pydantic import BaseModel, ValidationError
import requests
import os
import random
from uuid import uuid4
from skyfield.api import load, Topos
from skyfield.api import EarthSatellite
from skyfield.api import Loader

app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

API_KEY = "2ec61f431b6e20db0262d465508aa20c2bd90e11"
client_data_map = {}

# -------- Satellite Model --------
class Satellite(BaseModel):
    id: int
    name: str
    tle1: str
    tle2: str

# -------- Fetch + Match Logic --------
def fetch_satellites():
    try:
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
        response = requests.get(url)
        response.raise_for_status()

        lines = response.text.strip().splitlines()
        satellites = []

        # TLEs come in blocks of 3 lines: name, line1, line2
        for i in range(0, len(lines), 3):
            try:
                name = lines[i].strip()
                line1 = lines[i+1].strip()
                line2 = lines[i+2].strip()
                sat = EarthSatellite(line1, line2, name)
                satellites.append((sat, name, line1, line2))
            except Exception as e:
                print(f"[TLE PARSE ERROR] Line {i}: {e}")
                continue

        print(f"[TLE] Loaded {len(satellites)} valid satellites.")
        return satellites

    except Exception as e:
        print("[CELESTRAK FETCH ERROR]", e)
        return []


def match_satellite_by_az_el(client_az, client_el, observer_lat=28.61, observer_lon=77.23):
    ts = load.timescale()
    t = ts.now()
    observer = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon)
    observer_position = observer.at(t)

    matches = []
    for sat, name, line1, line2 in fetch_satellites():
        try:
            topocentric = (sat - observer).at(t)
            alt, az, _ = topocentric.altaz()
            azimuth, elevation = az.degrees, alt.degrees

            if abs(azimuth - client_az) < 5 and abs(elevation - client_el) < 5:
                matches.append({
                    "name": name,
                    "az": round(azimuth, 2),
                    "el": round(elevation, 2),
                    "tle_line1": line1,
                    "tle_line2": line2,
                })
        except Exception as e:
            print(f"[MATCH ERROR] {name}: {e}")
    return matches



# -------- SocketIO Events --------
@socketio.on("connect")
def handle_connect():
    emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] Dashboard connected: {request.sid}")

@socketio.on("client_data")
def handle_client_data(data):
    client_name = data.get("name",request.sid)
    client_id = data.get("ip", request.sid)
    client_data_map[client_id] = data
    print(f"📡 Broadcasting data for {len(client_data_map)} client(s)")
    socketio.emit("client_data_update", {"clients": list(client_data_map.values())})
    socketio.emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] Data received from {client_id}")

@socketio.on("fetch_satellite_match")
def handle_satellite_match(data):
    az = float(data.get("az", 0))
    el = float(data.get("el", 0))
    client_id = data.get("client_id", "unknown")

    matches = match_satellite_by_az_el(az, el)
    if matches:
        socketio.emit("matched_satellites", {
            "client_id": client_id,
            "matches": matches
        })
        socketio.emit("log", f"[Match] {len(matches)} satellite(s) matched AZ:{az} EL:{el}")
    else:
        socketio.emit("log", f"[No Match] No satellites found for AZ:{az}, EL:{el}")


# -------- REST APIs & Static --------
@app.route("/")
def index():
    return app.send_static_file("dashboard.html")

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(app.static_folder, "js"), filename)

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(app.static_folder, "css"), filename)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
