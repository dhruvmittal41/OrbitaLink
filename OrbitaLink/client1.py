import socketio

sio = socketio.Client()

@sio.event
def send_angles():
    while True:
        sio.emit('client_to_server',{'Azimuathal Angle': 45, 'Elevation Angle' : 23})
        sio.sleep(1)

@sio.event
def connect():
    print('connection established')
    sio.start_background_task(send_angles)    
    

@sio.event
def disconnect():
    print('disconnected from server')

sio.connect('http://localhost:5000')
sio.wait()
