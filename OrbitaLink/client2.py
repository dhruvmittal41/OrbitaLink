import socketio

sio = socketio.Client()

def send_angles():
    while True:
        sio.emit('client_to_server',{'Current Az Angle': 45, 'Current El Angle' : 23})
        sio.sleep(1)

@sio.event
def connect():
    print('connection established')
    sio.start_background_task(send_angles)    


@sio.event
def server_to_client(data):
    print('message :', data)
    

@sio.event
def disconnect():
    print('disconnected from server')

sio.connect('http://localhost:5000')
sio.wait()
