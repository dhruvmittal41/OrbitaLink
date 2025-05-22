import eventlet
import socketio

sio = socketio.Server()
app = socketio.WSGIApp(sio)

@sio.event
def connect(sid, environ):
    print('Connected to Session ID:', sid)

@sio.event
def client_to_server(sid, data):
    print('message :', data)
    
# @sio.event
# def server_to_client():
#     sio.emit('received_by_client', {'Updated Azimuathal Angle': 55, 'Updated Elevation Angle' : 50})
#     sio.sleep(1)

@sio.event
def disconnect(sid):
    print('Disconnected to Session ID:', sid)

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)