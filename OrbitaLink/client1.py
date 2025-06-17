import socketio
import time
import random
import requests

MAIN_SERVER_URL = "http://localhost:5000"
CLIENT_NAME = "Client A"

main_sio = socketio.Client()


@main_sio.event
def connect():
    main_sio.emit("register_client", {"name": CLIENT_NAME})


main_sio.connect("http://localhost:5000")


sio = socketio.Client()


@sio.event
def connect():
    print(f"{CLIENT_NAME} connected")
    sio.emit("register_client", {"name": CLIENT_NAME})
    sio.start_background_task(send_angles)


@sio.event
def disconnect():
    print(f"{CLIENT_NAME} disconnected")


def send_angles():
    while True:
        az = round(random.uniform(0, 360), 2)
        el = round(random.uniform(0, 360), 2)
        sio.emit("client_to_server", {"Azimuthal Angle": az, "Elevation Angle": el})
        time.sleep(1)


def get_server_port():
    try:
        res = requests.get(
            f"{MAIN_SERVER_URL}/get_server_for_client", params={"client": CLIENT_NAME}
        )
        if res.status_code == 200:
            return res.json().get("server_port")
    except Exception as e:
        print("Error getting server port:", e)
    return None


if __name__ == "__main__":
    while True:
        port = get_server_port()
        if port:
            try:
                SERVER_URL = f"http://localhost:{port}"
                sio.connect(SERVER_URL)
                sio.wait()
            except Exception as e:
                print(f"Retrying... failed to connect to {SERVER_URL}: {e}")
        else:
            print("Waiting for user to assign server...")
        time.sleep(3)
