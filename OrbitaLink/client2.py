import socketio
import time
import random

SERVER_URL = "http://localhost:5000"
CLIENT_NAME = "002"

sio = socketio.Client()


@sio.event
def connect():
    print(f"[{CLIENT_NAME}] Connected to server")
    sio.start_background_task(send_data)


@sio.event
def disconnect():
    print(f"[{CLIENT_NAME}] Disconnected from server")


def send_data():
    while True:
        data = {
            "name": CLIENT_NAME,
            "ip": "192.168.301.102",
            "lat": "28.890°N",
            "lon": "77.557°E",
            "tle_line1": "TLE1 - CLIENT 002",
            "tle_line2": "TLE2 - CLIENT 002",
            "az": round(random.uniform(0, 360), 2),
            "el": round(random.uniform(0, 90), 2),
            "time": time.strftime("%I:%M:%S %p IST"),
            "temp": round(random.uniform(20, 35), 1),
            "humidity": round(random.uniform(40, 80), 1),
        }
        sio.emit("client_data", data)
        time.sleep(2)


if __name__ == "__main__":
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"Retrying in 3 seconds... Error: {e}")
            time.sleep(3)
