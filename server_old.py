from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
from datetime import datetime
from skyfield.api import load, Topos, EarthSatellite
import requests
import os
import time


# Mapping of satellite names to NORAD IDs (you can expand this)
SAT_NAME_TO_NORAD = {
    "ISS (ZARYA)": 25544,
    "NOAA 15": 25338,
    "NOAA 18": 28654,
    "NOAA 19": 33591,
    "TERRA": 25994,
    "AQUA": 27424
}




app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

# ✅ Registry to store all connected Field Units and their sensor data
FU_REGISTRY = {}  # Maps FU ID to {sensor_data, timestamp, ...}
field_units = {}  # Stores satellite + AZ/EL info for FUs

# ------------ Utility: Fetch TLE from SatNOGS ------------ #
def fetch_tle_from_celestrak(norad_id):
    try:
        url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=TLE"
        response = requests.get(url)
        lines = response.text.strip().split("\n")
        if len(lines) >= 3:
            return lines[1], lines[2]  # Line 1 and Line 2 of TLE
        else:
            print(f"[TLE ERROR] Invalid TLE response for NORAD ID {norad_id}")
    except Exception as e:
        print(f"[CELESTRAK ERROR] {e}")
    return None, None


# ------------ Utility: Compute AZ/EL ------------ #


# ------------ SOCKET.IO EVENTS ------------ #

@socketio.on("connect")
def handle_connect():
    print(f"[CONNECT] Dashboard connected: {request.sid}")
    emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] Dashboard connected")

@socketio.on("field_unit_data")
def handle_field_unit_data(data):
    fu_id = data.get("fu_id")
    sensor_data = data.get("sensor_data", {})

    if fu_id:
        # Store in both registries
        FU_REGISTRY[fu_id] = {
            "fu_id": fu_id,
            "sensor_data": sensor_data,
            "timestamp": time.time()
        }
        field_units.setdefault(fu_id, {})  # Ensure entry exists
        field_units[fu_id]["sensor_data"] = sensor_data

        print(f"[FU DATA] Received from {fu_id}: {sensor_data}")

        # Broadcast to dashboards
        socketio.emit("client_data_update", {"clients": list(FU_REGISTRY.values())})

def compute_az_el(tle1, tle2, name, observer_lat, observer_lon):
     try:
        ts = load.timescale()
        t = ts.now()
        satellite = EarthSatellite(tle1, tle2, name)
        observer = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon)
        difference = satellite - observer
        topocentric = difference.at(t)
        alt, az, _ = topocentric.altaz()
        return round(az.degrees, 2), round(alt.degrees, 2)
     except Exception as e:
        print(f"[AZ/EL COMPUTE ERROR] {e}")
        return None, None


@socketio.on("select_satellite")
def handle_satellite_selection(data):
    fu_id = data.get("fu_id")
    sat_name = data.get("satellite_name")
    sensor_data = field_units.get(fu_id, {}).get("sensor_data", {})

    norad_id = SAT_NAME_TO_NORAD.get(sat_name)

    if not norad_id:
        print(f"[ERROR] No NORAD ID found for {sat_name}")
        return

    latitude = sensor_data.get("Latitude")
    longitude = sensor_data.get("Longitude")

    if latitude is None or longitude is None:
        print(f"[ERROR] Latitude/Longitude not found for {fu_id}")
        return

    tle1, tle2 = fetch_tle_from_celestrak(norad_id)
    if tle1 and tle2:
        az, el = compute_az_el(tle1, tle2, sat_name, latitude, longitude)
        if az is not None and el is not None:
            field_units.setdefault(fu_id, {})
            field_units[fu_id].update({
                "satellite": sat_name,
                "az": az,
                "el": el
            })

            socketio.emit("az_el_update", {
                "fu_id": fu_id,
                "az": az,
                "el": el
            })

            socketio.emit("az_el_command", {
                "fu_id": fu_id,
                "az": az,
                "el": el
            })

            print(f"[AZ/EL] {fu_id} => AZ: {az}°, EL: {el}°")
    else:
        print(f"[ERROR] TLE not found for NORAD ID {norad_id}")



@socketio.on("poll_az_el")
def handle_poll_az_el(data):
    fu_id = data.get("fu_id")
    fu_data = field_units.get(fu_id)
    if fu_data:
        emit("az_el_update", {
            "fu_id": fu_id,
            "az": fu_data.get("az"),
            "el": fu_data.get("el")
        })
        print(f"[POLL] Sent AZ/EL to {fu_id}: AZ={fu_data.get('az')}, EL={fu_data.get('el')}")
    else:
        print(f"[POLL ERROR] No data found for {fu_id}")

@socketio.on("request_clients")
def handle_request_clients():
    emit("client_data_update", {"clients": list(FU_REGISTRY.values())})

# ------------ STATIC FILE ROUTES ------------ #
@app.route("/")
def index():
    return app.send_static_file("dashboard.html")

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(app.static_folder, "js"), filename)

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(app.static_folder, "css"), filename)

# ------------ MAIN ------------ #
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)
