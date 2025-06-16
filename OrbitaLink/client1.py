import socketio
import time

sio = socketio.Client()

def send_angles():
    while True:
        sio.emit('client_to_server', {'Azimuathal Angle': 45, 'Elevation Angle': 23})
        time.sleep(1)

@sio.event
def connect():
    print('Connected to server')
    sio.start_background_task(send_angles)

@sio.event
def disconnect():
    print('Disconnected from server')

sio.connect('http://127.0.0.1:5000')
sio.wait()
