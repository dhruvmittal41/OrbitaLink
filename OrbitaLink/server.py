from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit

app = Flask(__name__, static_folder='.')
socketio = SocketIO(app, cors_allowed_origins="*")

clients = set()
servers = set()

@app.route('/')
def index():
    return send_from_directory('.', 'menu.html')

@socketio.on('register_client')
def handle_client_register(data):
    sid = request.sid
    clients.add(sid)
    print(f"Client registered: {sid}")
    update_status()

@socketio.on('register_server')
def handle_server_register(data):
    sid = request.sid
    servers.add(sid)
    print(f"Server registered: {sid}")
    update_status()

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    clients.discard(sid)
    servers.discard(sid)
    print(f"Disconnected: {sid}")
    update_status()

def update_status():
    socketio.emit('status_update', {
        'clients': list(clients),
        'servers': list(servers)
    })

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
