### main server: server.py

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__, static_folder='static')
socketio = SocketIO(app, cors_allowed_origins="*")

client_server_map = {}  # client_name -> port
connections = {
    "clients": [],
    "servers": []
}

@app.route('/')
def index():
    return send_from_directory('.', 'menu.html')

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(app.static_folder, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(app.static_folder, 'js'), filename)

@app.route('/set_server_for_client', methods=['POST'])
def set_server_for_client():
    data = request.json
    client_server_map[data["client"]] = data["port"]
    return jsonify({"status": "ok"})

@app.route('/get_server_for_client')
def get_server_for_client():
    client = request.args.get("client")
    port = client_server_map.get(client)
    return jsonify({"server_port": port})

@app.route('/register_activity', methods=['POST'])
def register_activity():
    data = request.json
    c = data.get("client")
    s = data.get("server")
    if c and c not in connections["clients"]:
        connections["clients"].append(c)
    if s and s not in connections["servers"]:
        connections["servers"].append(s)
    socketio.emit('status_update', connections)
    return jsonify({"status": "OK"}), 200

@app.route('/get_connections')
def get_connections():
    return jsonify(connections)

@socketio.on('connect')
def on_connect():
    emit('status_update', connections)

@socketio.on('register_client')
def register_client(data):
    name = data.get("name")
    if name and name not in connections["clients"]:
        connections["clients"].append(name)
        socketio.emit('status_update', connections)

@socketio.on('register_server')
def register_server(data):
    name = data.get("name")
    if name and name not in connections["servers"]:
        connections["servers"].append(name)
        socketio.emit('status_update', connections)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
