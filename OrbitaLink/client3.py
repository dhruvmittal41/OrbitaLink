import socketio
import time
import random
import requests
import geocoder
from skyfield.api import load, wgs84, EarthSatellite

# Initialize
ts = load.timescale()
sio = socketio.Client()
SERVER_URL = "https://musical-computing-machine-pjwjxqp7pqx6h777v-8080.app.github.dev/"
FU_ID = None  # Assigned by server

# Auto-detect location via IP
g = geocoder.ip('me')
LATITUDE = g.latlng[0] if g.latlng else 28.6139
LONGITUDE = g.latlng[1] if g.latlng else 77.2090
ALTITUDE = 216  # Estimated

# Sensor simulation
def generate_sensor_data():
    return {
        "temperature": round(random.uniform(20, 35), 1),
        "humidity": round(random.uniform(30, 70), 1),
        "pressure": round(random.uniform(990, 1020), 1),
        "Latitude": LATITUDE,
        "Longitude": LONGITUDE
    }

# Space-Track credentials (secure these in real applications)
SPACETRACK_USERNAME = 'mittaldhruv41@gmail.com'
SPACETRACK_PASSWORD = 'dhruvmittal4123'
TLE_CACHE = {}

# Get TLE from Space-Track
def get_tle(norad_id):
    login_url = "https://www.space-track.org/ajaxauth/login"
    data_url = f"https://www.space-track.org/basicspacedata/query/class/tle_latest/NORAD_CAT_ID/{norad_id}/orderby/ORDINAL asc/limit/1/format/tle"
    session = requests.Session()

    login = session.post(login_url, data={'identity': SPACETRACK_USERNAME, 'password': SPACETRACK_PASSWORD})
    if login.status_code != 200:
        raise Exception("Space-Track login failed")

    response = session.get(data_url)
    lines = response.text.strip().split('\n')
    if len(lines) >= 2:
        return lines[0], lines[1]
    else:
        raise Exception(f"TLE fetch failed for NORAD {norad_id}. Got: {lines}")

def get_tle_cached(norad_id):
    if norad_id not in TLE_CACHE:
        print(f"🌐 Fetching TLE for NORAD ID {norad_id}")
        TLE_CACHE[norad_id] = get_tle(norad_id)
    return TLE_CACHE[norad_id]

# Compute AZ/EL
def compute_az_el(norad_id, lat, lon, alt=0):
    try:
        tle1, tle2 = get_tle_cached(norad_id)
        satellite = EarthSatellite(tle1, tle2, 'satellite', ts)
        observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)
        t = ts.now()
        difference = satellite - observer
        topocentric = difference.at(t)
        alt, az, _ = topocentric.altaz()
        return round(az.degrees, 2), round(alt.degrees, 2)
    except Exception as e:
        print(f"⚠️ Error computing AZ/EL: {e}")
        return None, None

# ===== SOCKET EVENTS =====
@sio.event
def connect():
    print("✅ Connected to server")
    send_initial_sensor_data()
    sio.start_background_task(send_sensor_data)
    sio.start_background_task(poll_az_el_loop)

@sio.on("assign_fu_id")
def on_assign_fu_id(data):
    global FU_ID
    FU_ID = data.get("fu_id")
    print(f"🎯 Assigned FU_ID: {FU_ID}")

@sio.on("az_el_update")
def on_az_el_update(data):
    if data.get("fu_id") != FU_ID:
        return
    norad_id = data.get("norad_id")
    print(f"🛰️ Received NORAD ID: {norad_id}")
    try:
        az, el = compute_az_el(norad_id, LATITUDE, LONGITUDE, ALTITUDE)
        if az is not None and el is not None:
            print(f"📡 Computed AZ: {az:.2f}°, EL: {el:.2f}°")
            sio.emit("az_el_result", {
                "fu_id": FU_ID,
                "norad_id": norad_id,
                "az": az,
                "el": el,
                "gps": {
                    "lat": LATITUDE,
                    "lon": LONGITUDE,
                    "alt": ALTITUDE
                }
            })
    except Exception as e:
        print(f"⚠️ Error in AZ/EL update handler: {e}")

# Initial trigger
def send_initial_sensor_data():
    global FU_ID
    data = {
        "fu_id": FU_ID,
        "sensor_data": generate_sensor_data()
    }
    print("📤 Sending initial sensor data:", data)
    sio.emit("field_unit_data", data)

# Send data every 5s
def send_sensor_data():
    while True:
        if FU_ID:
            data = {
                "fu_id": FU_ID,
                "sensor_data": generate_sensor_data()
            }
            print("📤 Sending sensor data:", data)
            sio.emit("field_unit_data", data)
        time.sleep(5)

# Poll AZ/EL every 5s
def poll_az_el_loop():
    while True:
        if FU_ID:
            sio.emit("poll_az_el", {"fu_id": FU_ID})
        time.sleep(5)

# ===== MAIN =====
if __name__ == "__main__":
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"❌ Connection error: {e}. Retrying in 3s...")
            time.sleep(3)
