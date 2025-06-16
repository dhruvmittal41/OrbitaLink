import socketio
import random
import time

# Create Socket.IO client instance
sio = socketio.Client()

# Background task to send random angle values
def send_angles():
    while True:
        azimuth = random.uniform(0, 360)
        elevation = random.uniform(0, 360)
        sio.emit('client_to_server', {
            'Azimuathal Angle': round(azimuth, 2),
            'Elevation Angle': round(elevation, 2)
        })
        time.sleep(1)

# Event handler for successful connection
@sio.event
def connect():
    print("✅ Connected to server")
    sio.emit('register_client', {})  # Notify server this is a client
    sio.start_background_task(send_angles)

# Event handler for disconnection
@sio.event
def disconnect():
    print("❌ Disconnected from server")

# Connect to the server
sio.connect('http://127.0.0.1:5000')
sio.wait()
