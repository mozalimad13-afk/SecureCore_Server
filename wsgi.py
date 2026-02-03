"""
WSGI Entry Point for Production Deployment
Use with Gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""
from app import create_app, create_socketio_app

# Create application with WebSocket support
app, socketio = create_socketio_app()

if __name__ == '__main__':
    socketio.run(app)
