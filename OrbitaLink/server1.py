import socketio
import time

# Create Socket.IO client instance
sio = socketio.Client()

# Event when connected to the main Flask-SocketIO server
@sio.event
def connect():
    print("✅ Server1 connected to Flask server")
    sio.emit('register_server', {})  # Let the Flask backend know this is a "server" agent

# Event when disconnected
@sio.event
def disconnect():
    print("❌ Server1 disconnected")

# Optional - Keep connection alive (you could send some data too)
def keep_alive():
    while True:
        sio.sleep(10)  # Can be used to emit heartbeats or server status if needed

# Connect to the Flask server
sio.connect('http://127.0.0.1:5000')
sio.start_background_task(keep_alive)
sio.wait()
