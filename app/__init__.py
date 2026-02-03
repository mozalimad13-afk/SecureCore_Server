"""
Flask Application Factory
Creates and configures the Flask application with all extensions, blueprints, and middleware
"""
from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
from pathlib import Path

# Compatibility shim for older joblib artifacts.
# Some saved pipelines were pickled referencing `validators.FeatureOrderValidator`.
# We provide an in-repo no-op implementation at `app.validators` and alias it here
# as the top-level module name `validators` so joblib can unpickle successfully.
import sys
from app import validators as _validators_shim

sys.modules.setdefault("validators", _validators_shim)

from config import get_config
from app.extensions import db, migrate, limiter, jwt
from app.utils.logger import setup_logging
from app.middleware.security_headers import add_security_headers
from app.middleware.error_handler import register_error_handlers
from app.middleware.csrf import init_csrf_protection
from app.utils.scheduler import run_scheduler


def create_app(config_name=None):
    """
    Application factory pattern for creating Flask app
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Ensure required directories exist
    ensure_directories(app)
    
    # Setup logging
    setup_logging(app)
    app.logger.info(f"Starting SecureCore IDS Backend - {config_name or 'development'} mode")
    app.logger.info(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Initialize extensions
    initialize_extensions(app)
    
    # Register blueprints (API routes)
    register_blueprints(app)
    
    # Apply middleware
    apply_middleware(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring"""
        return jsonify({
            'status': 'healthy',
            'service': 'SecureCore IDS API',
            'version': '1.0.0'
        }), 200
    
    @app.route('/', methods=['GET'])
    def index():
        """Root endpoint"""
        return jsonify({
            'message': 'SecureCore IDS API',
            'version': '1.0.0',
            'docs': '/api/docs',
            'openapi': '/api/openapi.json',
            'legacy_docs': '/api/docs-static'
        }), 200
    
    # Start background scheduler
    run_scheduler(app)
    
    app.logger.info("Application initialized successfully")
    return app


def ensure_directories(app):
    """Ensure required directories exist"""
    directories = [
        app.config['LOG_DIR'],
        app.config['UPLOAD_FOLDER'],
        app.config['BACKUP_DIR'],
        app.config['DOWNLOADS_DIR'],
        Path(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')).parent,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def initialize_extensions(app):
    """Initialize Flask extensions"""
    # Database
    db.init_app(app)
    migrate.init_app(app, db)
    
    # JWT Authentication
    jwt.init_app(app)
    
    # Rate Limiting
    if app.config['RATELIMIT_ENABLED']:
        limiter.init_app(app)
    
    # CORS
    if app.config['CORS_ENABLED']:
        CORS(app, 
             origins=app.config['CORS_ORIGINS'],
             supports_credentials=app.config['CORS_SUPPORTS_CREDENTIALS'],
             expose_headers=['X-CSRF-Token'])
    
    # CSRF Protection
    init_csrf_protection(app)
    
    app.logger.info("Extensions initialized")


def register_blueprints(app):
    """Register all API blueprints"""
    from app.blueprints.auth import auth_bp
    from app.blueprints.alerts import alerts_bp
    from app.blueprints.tokens import tokens_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.blocklist import blocklist_bp
    from app.blueprints.whitelist import whitelist_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.settings import settings_bp
    from app.blueprints.subscription import subscription_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.downloads import downloads_bp
    from app.blueprints.openapi_docs import openapi_bp
    from app.blueprints.docs import docs_bp
    from app.blueprints.payment_methods import payment_methods_bp
    from app.blueprints.devices import devices_bp
    from app.blueprints.locations import locations_bp
    from app.blueprints.members import members_bp
    from app.blueprints.members_delete import members_delete_bp

    # Swagger UI (local assets, no CDN)
    from flask_swagger_ui import get_swaggerui_blueprint
    swaggerui_bp = get_swaggerui_blueprint(
        base_url='/api/docs',
        api_url='/api/openapi.json',
        config={'app_name': 'SecureCore IDS API'},
    )
    
    # Register with /api/v1 prefix for frontend compatibility
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(alerts_bp, url_prefix='/api/v1/alerts')
    app.register_blueprint(tokens_bp, url_prefix='/api/v1/tokens')
    app.register_blueprint(reports_bp, url_prefix='/api/v1/reports')
    app.register_blueprint(blocklist_bp, url_prefix='/api/v1/blocklist')
    app.register_blueprint(whitelist_bp, url_prefix='/api/v1/whitelist')
    app.register_blueprint(notifications_bp, url_prefix='/api/v1/notifications')
    app.register_blueprint(settings_bp, url_prefix='/api/v1/settings')
    app.register_blueprint(subscription_bp, url_prefix='/api/v1/subscription')
    app.register_blueprint(admin_bp, url_prefix='/api/v1/admin')
    app.register_blueprint(downloads_bp, url_prefix='/api/v1/downloads')
    # OpenAPI JSON + /api/endpoints (generated from code)
    app.register_blueprint(openapi_bp, url_prefix='/api')
    # Metadata summary for frontend
    app.register_blueprint(docs_bp, url_prefix='/api')
    # Swagger UI (renders /api/openapi.json)
    app.register_blueprint(swaggerui_bp)
    app.register_blueprint(payment_methods_bp, url_prefix='/api/v1')
    app.register_blueprint(devices_bp, url_prefix='/api/v1/devices')
    app.register_blueprint(locations_bp, url_prefix='/api/v1')
    app.register_blueprint(members_bp, url_prefix='/api/v1/members')
    app.register_blueprint(members_delete_bp, url_prefix='/api/v1/members')
    
    app.logger.info("Blueprints registered with /api/v1 prefix")



def apply_middleware(app):
    """Apply middleware layers"""
    # Security headers
    app.after_request(add_security_headers)
    
    app.logger.info("Middleware applied")


def create_socketio_app(app=None):
    """
    Create Socket.IO application for WebSocket support
    
    Args:
        app: Flask application instance (created if not provided)
    
    Returns:
        tuple: (Flask app, SocketIO instance)
    """
    if app is None:
        app = create_app()
    
    # Initialize Socket.IO with async mode
    socketio = SocketIO(
        app,
        cors_allowed_origins=app.config['CORS_ORIGINS'],
        async_mode='threading',  # or 'eventlet'/'gevent' for production
        ping_interval=app.config['WS_PING_INTERVAL'],
        ping_timeout=app.config['WS_PING_TIMEOUT'],
        max_http_buffer_size=app.config['WS_MAX_MESSAGE_SIZE'],
    )

    # Expose the running Socket.IO instance to request handlers/blueprints.
    # This avoids importing from entrypoints (which can create a second app).
    app.extensions['socketio'] = socketio
    
    # Register WebSocket handlers
    from app.websocket.server import register_websocket_handlers
    register_websocket_handlers(socketio, flask_app=app)

    # Best-effort ML model load (keeps server up even if artifacts missing)
    try:
        from app.ml.inference import get_inference_engine
        from config import Config

        engine = get_inference_engine()
        binary_path = str(Config.ML_MODELS_DIR / Config.ML_BINARY_MODEL_FILE)
        multiclass_path = str(Config.ML_MODELS_DIR / Config.ML_MULTICLASS_MODEL_FILE)
        engine.load_models(binary_path=binary_path, classification_path=multiclass_path)
        app.logger.info(f"Loaded ML models: {Config.ML_BINARY_MODEL_FILE} + {Config.ML_MULTICLASS_MODEL_FILE}")
    except Exception:
        app.logger.exception("ML models not loaded (using mock inference)")
    
    app.logger.info("WebSocket server initialized")
    
    return app, socketio
