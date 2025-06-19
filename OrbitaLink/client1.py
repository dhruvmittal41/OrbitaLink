import socketio
import time

# Configuration
SERVER_URL = "http://localhost:5000"
CLIENT_NAME = "Client A"              # Set the name for this client
CLIENT_IP = "192.168.1.5"             # Simulated IP address
AZIMUTH = 110.0                       # Default azimuth
ELEVATION = 35.0                      # Default elevation

# Initialize Socket.IO client
sio = socketio.Client()

@sio.event
def connect():
    print(f"✅ Connected to server as {CLIENT_NAME}")
    sio.start_background_task(send_data)

def send_data():
    while True:
        data = {
            "name": CLIENT_NAME,
            "ip": CLIENT_IP,
            "az": AZIMUTH,
            "el": ELEVATION,
            "time": time.strftime("%I:%M:%S %p")
        }

        print("📤 Sending data:", data)
        sio.emit("client_data", data)
        time.sleep(5)

@sio.event
def disconnect():
    print("❌ Disconnected from server")

if __name__ == "__main__":
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"⚠️ Error connecting, retrying in 3 seconds: {e}")
            time.sleep(3)
