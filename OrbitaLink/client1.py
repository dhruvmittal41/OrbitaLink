import socketio
import requests
import time


API_KEY = "2ec61f431b6e20db0262d465508aa20c2bd90e11"

SERVER_URL = "http://localhost:5000"
sio = socketio.Client()


@sio.event
def connect():
    print("Connected to dashboard server")
    sio.start_background_task(send_satnogs_data)


def fetch_satellites():
    headers = {"Authorization": f"Token {API_KEY}"}

    try:
        response = requests.get(
            "https://db.satnogs.org/api/satellites/", headers=headers, timeout=5
        )
        response.raise_for_status()
        return response.json()[:5]
    except requests.exceptions.HTTPError as http_err:
        print(f"[HTTP ERROR] {http_err} - {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"[REQUEST ERROR] {req_err}")
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}")

    return []


def send_satnogs_data():
    satellites = fetch_satellites()
    while True:
        for sat in satellites:
            data = {
                "name": sat.get("name"),
                "ip": "db.satnogs.org",
                "lat": "N/A",
                "lon": "N/A",
                "tle_line1": sat.get("tle1"),
                "tle_line2": sat.get("tle2"),
                "az": 0,  # Placeholder
                "el": 0,  # Placeholder
                "time": time.strftime("%I:%M:%S %p IST"),
                "temp": "N/A",
                "humidity": "N/A",
            }
            sio.emit("client_data", data)
            time.sleep(2)  # Send every 2 seconds
        time.sleep(10)


if __name__ == "__main__":
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"Retrying in 3 seconds... Error: {e}")
            time.sleep(3)
