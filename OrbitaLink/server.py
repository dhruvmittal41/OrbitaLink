import socketio
from aiohttp import web

# Create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Serve the index.html page
async def index(request):
    return web.FileResponse('index.html')  # must be in same folder

app.router.add_get('/', index)

# Handle data from Python client
@sio.on('client_to_server')
async def handle_angles(sid, data):
    await sio.emit('angle_update', data)  # broadcast to web clients

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

# Run the app
if __name__ == '__main__':
  web.run_app(app, port=5000, host='0.0.0.0')
