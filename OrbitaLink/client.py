import time
import requests
import geocoder
import serial
import socketio
import uuid
from skyfield.api import load, wgs84, EarthSatellite

# === Configuration ===
SERVER_URL = "http://localhost:8080"
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 9600
ALTITUDE = 216  # meters

# === Unique FU ID ===
def get_mac_address():
    mac = uuid.getnode()
    return ':'.join(f"{(mac >> ele) & 0xff:02x}" for ele in range(40, -1, -8))

FU_ID = get_mac_address()

# === Geo IP Location ===
g = geocoder.ip('me')
LATITUDE = g.latlng[0] if g.latlng else 28.6139
LONGITUDE = g.latlng[1] if g.latlng else 77.2090

# === Socket.IO Client ===
sio = socketio.Client()

# === TLE Cache ===
TLE_CACHE = {}
ts = load.timescale()

# === Serial Setup ===
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"✅ Connected to Arduino on {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Failed to open serial port {SERIAL_PORT}: {e}")
    ser = None

# === Sensor Reader ===
def generate_sensor_data():
    if not ser or not ser.is_open:
        print("⚠️ Serial port not available.")
        return {}
    try:
        for _ in range(5):
            line = ser.readline().decode('utf-8', errors='ignore').strip()
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
        print("⚠️ No valid sensor data line found.")
    except Exception as e:
        print(f"⚠️ Error reading serial: {e}")
    return {}

# === TLE Fetching ===
def get_tle_by_name(sat_name):
    if sat_name in TLE_CACHE:
        return TLE_CACHE[sat_name]
    
    print(f"🌐 Requesting TLE for {sat_name} from server")
    try:
        response = requests.get(f"{SERVER_URL}/api/tle_by_name", params={"name": sat_name})
        response.raise_for_status()
        data = response.json()
        tle1, tle2 = data["tle_line1"], data["tle_line2"]
        TLE_CACHE[sat_name] = (tle1, tle2)
        return tle1, tle2
    except Exception as e:
        print(f"❌ TLE fetch failed for {sat_name}: {e}")
        return None, None

# === AZ/EL Computation ===
def compute_az_el_by_name(sat_name, lat, lon, alt=0):
    try:
        tle1, tle2 = get_tle_by_name(sat_name)
        if not tle1 or not tle2:
            raise Exception("No valid TLE lines received.")
        satellite = EarthSatellite(tle1, tle2, sat_name, ts)
        observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)
        t = ts.now()
        difference = satellite - observer
        topocentric = difference.at(t)
        alt, az, _ = topocentric.altaz()
        return round(az.degrees, 2), round(alt.degrees, 2)
    except Exception as e:
        print(f"⚠️ Error computing AZ/EL: {e}")
        return None, None

# === Socket.IO Events ===
@sio.event
def connect():
    print("✅ Connected to server")
    send_initial_data()
    sio.start_background_task(send_sensor_data)
    sio.start_background_task(poll_az_el_loop)

@sio.on("az_el_update")
def on_az_el_update(data):
    if data.get("fu_id") != FU_ID:
        return
    sat_name = data.get("satellite_name")
    fu_id = data.get("fu_id")
    print(f"🛰️ Received satellite: {sat_name} for FU: {fu_id}")

    if not sat_name or sat_name == "undefined" or fu_id != FU_ID:
        print("⚠️ Invalid or mismatched satellite update")
        return

    print(f"🌐 Requesting TLE for {sat_name} from server")
    az, el = compute_az_el_by_name(sat_name, LATITUDE, LONGITUDE, ALTITUDE)
    if az is not None and el is not None:
        print(f"📡 Computed AZ: {az:.2f}°, EL: {el:.2f}°")
        sio.emit("az_el_result", {
            "fu_id": FU_ID,
            "az": az,
            "el": el,
            "satellite_name": sat_name,
            "gps": {
                "lat": LATITUDE,
                "lon": LONGITUDE,
                "alt": ALTITUDE
            }
        })
    else:
        print(f"⚠️ AZ/EL computation failed for {sat_name}")

# === Senders ===
def send_initial_data():
    data = {
        "fu_id": FU_ID,
        "sensor_data": generate_sensor_data()
    }
    print("📤 Sending initial sensor data", data)
    sio.emit("field_unit_data", data)

def send_sensor_data():
    while True:
        data = {
            "fu_id": FU_ID,
            "sensor_data": generate_sensor_data()
        }
        print("📤 Sending sensor data:", data)
        sio.emit("field_unit_data", data)
        time.sleep(5)

def poll_az_el_loop():
    while True:
        sio.emit("poll_az_el", {"fu_id": FU_ID})
        time.sleep(5)

# === Run Client ===
if __name__ == "__main__":
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"❌ Connection failed: {e}. Retrying in 3s...")
            time.sleep(3)
