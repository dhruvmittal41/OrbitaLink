import socketio
import time
import requests
import geocoder
import serial
from skyfield.api import load, wgs84, EarthSatellite
import uuid

# === Constants ===
SERVER_URL = "https://musical-computing-machine-pjwjxqp7pqx6h777v-8080.app.github.dev/"
SERIAL_PORT = '/dev/ttyACM0'  # Update if needed, e.g., /dev/ttyUSB0
BAUD_RATE = 9600
ALTITUDE = 216  # in meters

# === MAC Address as FU ID ===
def get_mac_address():
    mac = uuid.getnode()
    return ':'.join(f"{(mac >> ele) & 0xff:02x}" for ele in range(40, -1, -8))

FU_ID = get_mac_address()

# === Geo IP Location ===
g = geocoder.ip('me')
LATITUDE = g.latlng[0] if g.latlng else 28.6139
LONGITUDE = g.latlng[1] if g.latlng else 77.2090

# === Space-Track Setup ===
SPACETRACK_USERNAME = 'mittaldhruv41@gmail.com'
SPACETRACK_PASSWORD = 'dhruvmittal4123'
TLE_CACHE = {}

ts = load.timescale()
sio = socketio.Client()

# === Serial Connection Setup ===
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"✅ Connected to Arduino on {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Failed to open serial port {SERIAL_PORT}: {e}")
    ser = None

# === Real Sensor Data from Arduino ===
def generate_sensor_data():
    if not ser or not ser.is_open:
        print("⚠️ Serial port not available.")
        return {}

    try:
        line = ser.readline().decode('utf-8').strip()
        if line.startswith("Humidity:"):
            print(f"📥 From Arduino: {line}")
            parts = line.split()
            humidity = float(parts[1].replace('%', ''))
            temperature = float(parts[4].replace('°C', ''))
            return {
                "temperature": temperature,
                "humidity": humidity,
                "Latitude": LATITUDE,
                "Longitude": LONGITUDE
            }
    except Exception as e:
        print(f"⚠️ Error reading/parsing serial: {e}")

    return {}

# === TLE Fetching ===
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

# === Socket Events ===
@sio.event
def connect():
    print("✅ Connected to server")
    send_initial_sensor_data()
    sio.start_background_task(send_sensor_data)
    sio.start_background_task(poll_az_el_loop)

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
        else:
            print(f"⚠️ AZ/EL could not be computed for NORAD {norad_id}")
    except Exception as e:
        print(f"⚠️ Error computing AZ/EL: {e}")

# === Sensor Data Push ===
def send_initial_sensor_data():
    data = {
        "fu_id": FU_ID,
        "sensor_data": generate_sensor_data()
    }
    print("📤 Sending initial sensor data:", data)
    sio.emit("field_unit_data", data)

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

def poll_az_el_loop():
    while True:
        if FU_ID:
            sio.emit("poll_az_el", {"fu_id": FU_ID})
        time.sleep(5)

# === Main Loop ===
if __name__ == "__main__":
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"❌ Connection error: {e}. Retrying in 3s...")
            time.sleep(3)
