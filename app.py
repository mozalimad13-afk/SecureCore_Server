"""
Main Application Entry Point
Runs the Flask application with WebSocket support
"""
import os
from app import create_app, create_socketio_app

# Get configuration from environment
config_name = os.getenv('FLASK_ENV', 'development')

# Create Flask app with WebSocket support
app, socketio = create_socketio_app()

if __name__ == '__main__':
    # Development server
    host = app.config['HOST']
    port = app.config['PORT']
    debug = app.config['DEBUG']
    
    print(f"Starting SecureCore IDS Backend on {host}:{port}")
    print(f"Environment: {config_name}")
    print(f"Debug mode: {debug}")
    
    # Run with Socket.IO
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug,
        allow_unsafe_werkzeug=True,
    )
