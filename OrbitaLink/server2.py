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
    server_to_client(sid)
    # sio.emit('server_to_client', {'Target Az Angle': 55, 'Target El Angle' : 50}, to=sid)

def server_to_client(sid):
    sio.emit('server_to_client', {'Target Az Angle': 55, 'Target El Angle' : 50}, to=sid)
    sio.sleep(1)

@sio.event
def disconnect(sid, reason):
    if reason == sio.reason.CLIENT_DISCONNECT:
        print('the client disconnected')
    elif reason == sio.reason.SERVER_DISCONNECT:
        print('the server disconnected the client')
    else:
        print('disconnect reason:', reason)

if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)