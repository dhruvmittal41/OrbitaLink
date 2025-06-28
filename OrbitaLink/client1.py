import socketio
import time
import random
import requests
from skyfield.api import load, wgs84, EarthSatellite

ts = load.timescale()

sio = socketio.Client()
SERVER_URL = "https://musical-computing-machine-pjwjxqp7pqx6h777v-8080.app.github.dev/"
FU_ID = "FU-001"

import Adafruit_DHT

SENSOR = Adafruit_DHT.DHT11  # or DHT22
SENSOR_PIN = 4  

def generate_sensor_data():
    humidity, temperature = Adafruit_DHT.read_retry(SENSOR, SENSOR_PIN)
    if humidity is not None and temperature is not None:
        return {
            "temperature": round(temperature, 1),
            "humidity": round(humidity, 1),
            "pressure": round(random.uniform(990, 1020), 1),  # fake pressure
            "Latitude": LATITUDE,
            "Longitude": LONGITUDE
        }
    else:
        print("⚠️ Failed to read from DHT sensor. Sending dummy data.")
        return {
            "temperature": round(random.uniform(20, 35), 1),
            "humidity": round(random.uniform(30, 70), 1),
            "pressure": round(random.uniform(990, 1020), 1),
            "Latitude": LATITUDE,
            "Longitude": LONGITUDE
        }

TLE_CACHE = {}

import requests

# Replace with your actual Space-Track credentials
SPACETRACK_USERNAME = 'mittaldhruv41@gmail.com'
SPACETRACK_PASSWORD = 'dhruvmittal4123'

def get_tle(norad_id):
    login_url = "https://www.space-track.org/ajaxauth/login"
    data_url = f"https://www.space-track.org/basicspacedata/query/class/tle_latest/NORAD_CAT_ID/{norad_id}/orderby/ORDINAL asc/limit/1/format/tle"

    session = requests.Session()

    # Authenticate
    login = session.post(login_url, data={'identity': SPACETRACK_USERNAME, 'password': SPACETRACK_PASSWORD})
    if login.status_code != 200:
        raise Exception("Space-Track login failed")

    # Fetch TLE
    response = session.get(data_url)
    lines = response.text.strip().split('\n')
    if len(lines) >= 2:
        return lines[0], lines[1]
    else:
        raise Exception(f"TLE fetch failed from Space-Track for NORAD ID {norad_id}. Got: {lines}")


def compute_az_el(norad_id, lat, lon, alt=0):
    try:
        tle1, tle2 = get_tle_cached(norad_id)
        satellite = EarthSatellite(tle1, tle2, 'satellite', ts)
        observer = wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon, elevation_m=alt)

        t = ts.now()
        astrometric = satellite.at(t).observe(observer)
        apparent = astrometric.apparent()
        alt, az, distance = apparent.altaz()

        return round(az.degrees, 2), round(alt.degrees, 2)
    
    except Exception as e:
        print(f"⚠️ Error computing AZ/EL: {e}")
        return None, None


@sio.event
def connect():
    print("✅ Connected to server")
    sio.start_background_task(send_sensor_data)
    sio.start_background_task(poll_az_el_loop)

@sio.on("az_el_update")
def on_az_el_update(data):
    if data.get("fu_id") != FU_ID:
        return
    norad_id = data.get("norad_id")
    print(f"🛰️ Received NORAD ID: {norad_id}")
    try:
        tle1, tle2 = get_tle(norad_id)
        az, el = compute_az_el(tle1, tle2, LATITUDE, LONGITUDE, ALTITUDE)
        print(f"📡 Computed AZ: {az:.2f}°, EL: {el:.2f}°")
        sio.emit("az_el_result", {
            "fu_id": FU_ID,
            "norad_id": norad_id,
            "az": round(az, 2),
            "el": round(el, 2),
            "gps": {
                "lat": LATITUDE,
                "lon": LONGITUDE,
                "alt": ALTITUDE
            }
        })
    except Exception as e:
        print(f"⚠️ Error computing AZ/EL: {e}")

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

if __name__ == "__main__":
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"❌ Connection error: {e}. Retrying in 3s...")
            time.sleep(3)
