# =========================
# ✅ SERVER: Flask + Socket.IO (Wi-Fi Auto Integration with Ordered IDs & Cleanup)
# =========================
from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
import os
import time
import uuid

app = Flask(__name__, static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*")

SID_TO_FU = {}  # socket.id -> fu_id

SAT_NAME_TO_NORAD = {
    "ISS (ZARYA)": 25544,
    "NOAA 15": 25338,
    "NOAA 18": 28654,
    "NOAA 19": 33591,
    "TERRA": 25994,
    "AQUA": 27424
}

FU_REGISTRY = {}  # fu_id -> {sensor_data, timestamp}
field_units = {}  # fu_id -> {sensor_data, az, el, satellite, gps, ...}


def generate_ordered_fu_id():
    try:
        existing_ids = sorted([
            int(fu_id.split("-")[1]) for fu_id in FU_REGISTRY.keys()
            if fu_id.startswith("FU-") and fu_id.split("-")[1].isdigit()
        ])
        i = 1
        while i in existing_ids:
            i += 1
        return f"FU-{str(i).zfill(3)}"
    except Exception as e:
        print(f"[ERROR] Generating FU ID: {e}")
        return f"FU-{str(uuid.uuid4().hex[:6]).upper()}"


@socketio.on("connect")
def handle_connect():
    print(f"[CONNECT] Socket connected: {request.sid}")
    emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] New socket connection established")


@socketio.on("field_unit_data")
def handle_field_unit_data(data):
    fu_id = data.get("fu_id")
    sensor_data = data.get("sensor_data", {})

    if not isinstance(sensor_data, dict):
        print(f"[WARN] Invalid sensor_data format: {sensor_data}")
        return

    if not fu_id or fu_id == "None":
        fu_id = generate_ordered_fu_id()
        print(f"[AUTO-GEN FU ID] Assigned new ordered ID: {fu_id}")
        data["fu_id"] = fu_id

        socketio.emit("assign_fu_id", {"fu_id": fu_id}, to=request.sid)

    FU_REGISTRY[fu_id] = {
        "fu_id": fu_id,
        "sensor_data": sensor_data,
        "timestamp": time.time()
    }

    field_units.setdefault(fu_id, {})["sensor_data"] = sensor_data
    SID_TO_FU[request.sid] = fu_id

    socketio.emit("client_data_update", {"clients": list(FU_REGISTRY.values())})
    print(f"[FU DATA] Received from {fu_id}: {sensor_data}")


@socketio.on("select_satellite")
def handle_satellite_selection(data):
    fu_id = data.get("fu_id")
    sat_name = data.get("satellite_name")
    norad_id = SAT_NAME_TO_NORAD.get(sat_name)

    print(f"[SATELLITE SELECT] FU: {fu_id} -> Sat: {sat_name}, NORAD: {norad_id}")

    if not fu_id or not sat_name or not norad_id:
        print(f"[ERROR] Invalid satellite selection: {data}")
        return

    field_units.setdefault(fu_id, {})
    field_units[fu_id]["satellite"] = sat_name

    socketio.emit("az_el_update", {
        "fu_id": fu_id,
        "norad_id": norad_id
    })


@socketio.on("az_el_result")
def handle_az_el_result(data):
    fu_id = data.get("fu_id")
    az = data.get("az")
    el = data.get("el")
    norad_id = data.get("norad_id")
    gps = data.get("gps", {})

    if not all([fu_id, az is not None, el is not None]):
        print(f"[ERROR] Invalid AZ/EL result: {data}")
        return

    field_units.setdefault(fu_id, {}).update({
        "az": az,
        "el": el,
        "gps": gps,
        "norad_id": norad_id
    })

    print(f"[AZ/EL RESULT] {fu_id} -> AZ: {az}°, EL: {el}°")

    socketio.emit("az_el_command", {
        "fu_id": fu_id,
        "az": az,
        "el": el
    })


@socketio.on("poll_az_el")
def handle_poll_az_el(data):
    fu_id = data.get("fu_id")
    if not fu_id:
        print(f"[POLL ERROR] No FU ID provided in poll request")
        return

    fu_data = field_units.get(fu_id)
    if fu_data and "satellite" in fu_data:
        sat_name = fu_data["satellite"]
        norad_id = SAT_NAME_TO_NORAD.get(sat_name)
        if norad_id:
            emit("az_el_update", {
                "fu_id": fu_id,
                "norad_id": norad_id
            })
            print(f"[POLL] Re-sent NORAD ID {norad_id} to {fu_id}")
        else:
            print(f"[POLL ERROR] No NORAD ID for satellite: {sat_name}")
    else:
        print(f"[POLL ERROR] No satellite selected for {fu_id}")


@socketio.on("request_clients")
def handle_request_clients():
    emit("client_data_update", {"clients": list(FU_REGISTRY.values())})


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    fu_id = SID_TO_FU.pop(sid, None)
    if fu_id:
        print(f"[DISCONNECT] FU {fu_id} disconnected (SID: {sid})")
        FU_REGISTRY.pop(fu_id, None)
        field_units.pop(fu_id, None)
        emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] FU {fu_id} disconnected", broadcast=True)
        socketio.emit("client_data_update", {"clients": list(FU_REGISTRY.values())})


# =====================
# Optional: HTTP POST API for simple IoT devices
# =====================
@app.route("/api/fu", methods=["POST"])
def receive_fu_http():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    handle_field_unit_data(data)
    return {"status": "ok"}, 200


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
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)
