import json
import os
import time
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import socketio
import requests
from fastapi import Query
import urllib.parse
# --- Setup Async Socket.IO Server with Redis (for scaling) ---
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    ping_timeout=20,
    ping_interval=10,
    message_queue='redis://localhost:6379'
)

# --- FastAPI App and Static Files ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- ASGI App Wrapper ---
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)

@app.get("/")
async def get_dashboard():
    return FileResponse("static/dashboard.html")

# --- State and Configuration ---
SID_TO_FU = {}
FU_REGISTRY = {}
field_units = {}
DATA_PATH = "fu_data.json"

# --- Load Persisted State ---
if os.path.exists(DATA_PATH):
    with open(DATA_PATH, "r") as f:
        field_units.update(json.load(f))
    for fu_id, data in field_units.items():
        FU_REGISTRY[fu_id] = {
            "fu_id": fu_id,
            "sensor_data": data.get("sensor_data", {}),
            "timestamp": time.time(),
        }
    print(f"[BOOT] Restored field unit data for {len(field_units)} units.")

# --- Persistence Function ---
def save_field_units():
    with open(DATA_PATH, "w") as f:
        json.dump(field_units, f, indent=2)
    print("[SAVE] Field unit states saved.")

# --- Socket.IO Events ---
@sio.event
async def connect(sid, environ):
    print(f"[CONNECT] Socket connected: {sid}")
    await sio.emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] New socket connection established")
    await sio.emit("client_data_update", {"clients": list(FU_REGISTRY.values())})

@sio.on("field_unit_data")
async def handle_field_unit_data(sid, data):
    fu_id = data.get("fu_id")
    sensor_data = data.get("sensor_data", {})

    if not isinstance(sensor_data, dict) or not fu_id:
        print(f"[WARN] Invalid field unit data: {data}")
        return

    FU_REGISTRY[fu_id] = {
        "fu_id": fu_id,
        "sensor_data": sensor_data,
        "timestamp": time.time(),
        "satellite": field_units.get(fu_id, {}).get("satellite"),
        "az": field_units.get(fu_id, {}).get("az"),
        "el": field_units.get(fu_id, {}).get("el"),
        "gps": field_units.get(fu_id, {}).get("gps")
    }

    field_units.setdefault(fu_id, {})["sensor_data"] = sensor_data
    SID_TO_FU[sid] = fu_id

    await sio.emit("client_data_update", {"clients": list(FU_REGISTRY.values())})
    print(f"[FU DATA] Received from {fu_id}: {sensor_data}")

@sio.on("select_satellite")
async def handle_satellite_selection(sid, data):
    fu_id = data.get("fu_id")
    sat_name = data.get("satellite_name")

    print(f"[SATELLITE SELECT] FU: {fu_id} -> Sat: {sat_name}")

    if not fu_id or not sat_name:
        print(f"[ERROR] Invalid satellite selection: {data}")
        return

    # ✅ Update field_units and FU_REGISTRY immediately
    field_units.setdefault(fu_id, {})["satellite"] = sat_name
    FU_REGISTRY.setdefault(fu_id, {})["satellite"] = sat_name

    # ✅ Immediately acknowledge back
    await sio.emit("az_el_update", {
        "fu_id": fu_id,
        "satellite_name": sat_name
    })

    await sio.emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] {fu_id} selected {sat_name}")


@sio.on("az_el_result")
async def handle_az_el_result(sid, data):
    fu_id = data.get("fu_id")
    az = data.get("az")
    el = data.get("el")
    gps = data.get("gps", {})
    sat_name = data.get("satellite_name")

    if not all([fu_id, az is not None, el is not None]):
        print(f"[ERROR] Invalid AZ/EL result: {data}")
        return

    field_units.setdefault(fu_id, {}).update({
        "az": az,
        "el": el,
        "gps": gps,
        "satellite": sat_name
    })

    print(f"[AZ/EL RESULT] {fu_id} -> AZ: {az}°, EL: {el}°")

    await sio.emit("az_el_command", {
        "fu_id": fu_id,
        "az": az,
        "el": el
    })

@sio.on("poll_az_el")
async def handle_poll_az_el(sid, data):
    fu_id = data.get("fu_id")
    if not fu_id:
        print(f"[POLL ERROR] No FU ID provided")
        return

    sat_name = field_units.get(fu_id, {}).get("satellite")
    if sat_name:
        await sio.emit("az_el_update", {
            "fu_id": fu_id,
            "satellite_name": sat_name
        })
        print(f"[POLL] Re-sent satellite {sat_name} to {fu_id}")
    else:
        print(f"[POLL ERROR] No satellite selected for {fu_id}")

@sio.on("request_clients")
async def handle_request_clients(sid):
    for fu_id in FU_REGISTRY:
        if fu_id in field_units:
            FU_REGISTRY[fu_id].update({
                "satellite": field_units[fu_id].get("satellite"),
                "az": field_units[fu_id].get("az"),
                "el": field_units[fu_id].get("el"),
                "gps": field_units[fu_id].get("gps")
            })
    await sio.emit("client_data_update", {"clients": list(FU_REGISTRY.values())})

@sio.event
async def disconnect(sid):
    fu_id = SID_TO_FU.pop(sid, None)
    if fu_id:
        print(f"[DISCONNECT] FU {fu_id} disconnected (SID: {sid})")
        FU_REGISTRY.pop(fu_id, None)
        save_field_units()
        await sio.emit("log", f"[{datetime.now().strftime('%H:%M:%S')}] FU {fu_id} disconnected")
        await sio.emit("client_data_update", {"clients": list(FU_REGISTRY.values())})

# --- REST Endpoint for External FU Sensor Data ---
@app.post("/api/fu")
async def receive_fu_http(request: Request):
    data = await request.json()
    if not data:
        return {"error": "Invalid data"}
    await handle_field_unit_data(None, data)
    return {"status": "ok"}

@app.get("/api/satellites")
async def get_satellite_list():
    try:
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=TLE"
        response = requests.get(url)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch satellites from Celestrak")

        tle_text = response.text.strip().splitlines()

        # Every 3 lines: [name, line1, line2]
        names = [tle_text[i].strip() for i in range(0, len(tle_text), 3)]

        print(f"[CELESTRAK] Retrieved {len(names)} satellites")
        return names

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Satellite list error: {e}")


@app.get("/api/tle_by_name")
async def get_tle_by_name(name: str):
    try:
        url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=TLE"
        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch TLE from Celestrak")

        lines = response.text.strip().splitlines()

        # Every 3 lines: [name, line1, line2]
        for i in range(0, len(lines), 3):
            if lines[i].strip().upper() == name.strip().upper():
                tle_line1 = lines[i + 1].strip()
                tle_line2 = lines[i + 2].strip()
                return {
                    "name": name,
                    "tle_line1": tle_line1,
                    "tle_line2": tle_line2
                }

        raise HTTPException(status_code=404, detail=f"TLE not found for satellite: {name}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

