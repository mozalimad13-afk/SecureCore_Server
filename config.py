"""
Production Configuration for SecureCore IDS Backend
Manages environment variables, security settings, and application configuration
"""
import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = BASE_DIR.parent

class Config:
    """Base configuration"""
    
    # Flask Core
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')
    DEBUG = True
    TESTING = False
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    # Database
    # Database
    db_path = os.path.join(str(BASE_DIR), 'data', 'securecore.db')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{db_path}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Security - CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No time limit, rotation on every request
    CSRF_TOKEN_EXPIRY = timedelta(hours=24)
    
    # Security - JWT/Token Authentication
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # Support both browser (cookies) and mobile/agent (Authorization: Bearer)
    JWT_TOKEN_LOCATION = ['cookies', 'headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
    JWT_REFRESH_COOKIE_NAME = 'refresh_token_cookie'
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_SESSION_COOKIE = False  # Important to not use session cookies for JWT
    
    # API Token Configuration
    API_TOKEN_PREFIX = 'sk_live_securecore_'
    API_TOKEN_LENGTH = 48  # characters after prefix
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = 'memory://'  # Use Redis in production
    RATELIMIT_DEFAULT = "1000 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Per-endpoint rate limits
    RATE_LIMITS = {
        'auth_login': '5 per minute',
        'auth_register': '3 per hour',
        'ws_inference': '1000 per minute',  # Per user
        'api_general': '100 per minute',
        'admin_api': '200 per minute',
    }
    
    # CORS
    CORS_ENABLED = True
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:8080,http://localhost:5173,http://localhost:3000,http://127.0.0.1:8080,http://127.0.0.1:5173,http://192.168.0.131:8080').split(',')
    CORS_SUPPORTS_CREDENTIALS = True
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    }

    # Content Security Policy (applied globally)
    # Quick env var overrides (copy/paste):
    # export CSP_EXTRA_STYLE_SRC="https://cdn.tailwindcss.com,https://fonts.googleapis.com"
    # export CSP_EXTRA_SCRIPT_SRC="https://cdn.tailwindcss.com"
    # export CSP_EXTRA_CONNECT_SRC="wss://your-backend.com"
    # export CSP_EXTRA_IMG_SRC="https://your-cdn.com"
    CSP_ENABLED = True
    CSP_REPORT_ONLY = False
    # Can be comma-separated env var to inject additional sources safely
    CSP_EXTRA_SCRIPT_SRC = os.getenv('CSP_EXTRA_SCRIPT_SRC', '').split(',') if os.getenv('CSP_EXTRA_SCRIPT_SRC') else []
    CSP_EXTRA_STYLE_SRC = os.getenv('CSP_EXTRA_STYLE_SRC', '').split(',') if os.getenv('CSP_EXTRA_STYLE_SRC') else []
    CSP_EXTRA_CONNECT_SRC = os.getenv('CSP_EXTRA_CONNECT_SRC', '').split(',') if os.getenv('CSP_EXTRA_CONNECT_SRC') else []
    CSP_EXTRA_IMG_SRC = os.getenv('CSP_EXTRA_IMG_SRC', '').split(',') if os.getenv('CSP_EXTRA_IMG_SRC') else []

    # Default CSP directives (tune per deployment if needed)
    CSP_DEFAULT_SRC = ["'self'"]
    CSP_BASE_URI = ["'self'"]
    CSP_OBJECT_SRC = ["'none'"]
    CSP_FRAME_ANCESTORS = ["'none'"]
    CSP_FORM_ACTION = ["'self'"]
    # Pragmatic defaults: allow inline styles for Tailwind/Vite; tighten later with nonces/hashes.
    CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"]
    CSP_SCRIPT_SRC = ["'self'"]
    CSP_IMG_SRC = ["'self'", 'data:']
    CSP_FONT_SRC = ["'self'", 'data:']
    CSP_CONNECT_SRC = ["'self'", 'https:', 'wss:']
    CSP_UPGRADE_INSECURE_REQUESTS = True

    # HSTS (only meaningful over HTTPS; still safe to include in prod)
    HSTS_ENABLED = True
    HSTS_MAX_AGE = 31536000  # 1 year
    HSTS_INCLUDE_SUBDOMAINS = True
    HSTS_PRELOAD = False

    # Permissions Policy
    PERMISSIONS_POLICY = (
        "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
        "interest-cohort=()"
    )
    
    # Session Management
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # File Upload
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'csv', 'json', 'log'}
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = BASE_DIR / 'logs'
    LOG_FILE = LOG_DIR / 'app.log'
    ERROR_LOG_FILE = LOG_DIR / 'error.log'
    ACCESS_LOG_FILE = LOG_DIR / 'access.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Machine Learning Configuration
    ML_MODELS_DIR = PROJECT_ROOT / 'models'
    ML_DEFAULT_MODEL = 'rf_depth8_pipeline.joblib'
    ML_INPUT_FEATURES = 70
    ML_BATCH_SIZE = 32
    ML_INFERENCE_TIMEOUT = 5.0  # seconds

    # Model selection (joblib pipelines in `models/`)
    ML_BINARY_MODEL_FILE = os.getenv('ML_BINARY_MODEL_FILE', 'svm_poly_pipeline.joblib')
    ML_MULTICLASS_MODEL_FILE = os.getenv('ML_MULTICLASS_MODEL_FILE', 'knn_16_pipeline.joblib')
    
    # ML Model Metadata
    ML_METADATA_FILE = ML_MODELS_DIR / 'metadata.json'
    
    # WebSocket Configuration
    WS_MAX_CONNECTIONS_PER_USER = 5
    WS_MESSAGE_QUEUE_SIZE = 1000
    WS_PING_INTERVAL = 30  # seconds
    WS_PING_TIMEOUT = 10  # seconds
    WS_MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
    WS_INFERENCE_WORKERS = int(os.getenv('WS_INFERENCE_WORKERS', 4))
    
    # Firebase Cloud Messaging (FCM)
    FIREBASE_ENABLED = os.getenv('FIREBASE_ENABLED', 'true').lower() == 'true'
    FIREBASE_CREDENTIALS_FILE = BASE_DIR / 'our_key_file' / os.getenv(
        'FIREBASE_CREDENTIALS_FILENAME',
        'core-347f3-firebase-adminsdk-fbsvc-d13c8f835d.json'
    )
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'securecore-ids')
    
    # AES Encryption for FCM Tokens
    # CRITICAL: This key must be kept secure and never committed to version control
    # In production, load from secure key management service (e.g., AWS KMS, HashiCorp Vault)
    AES_ENCRYPTION_KEY = os.getenv(
        'AES_ENCRYPTION_KEY',
        'CHANGE-THIS-TO-SECURE-32-BYTE-KEY-IN-PRODUCTION!!'  # Must be 32 bytes for AES-256
    ).encode('utf-8')[:32].ljust(32, b'\0')  # Ensure exactly 32 bytes
    
    # Alert Configuration
    ALERT_SEVERITY_THRESHOLDS = {
        'critical': 0.95,  # confidence >= 95%
        'high': 0.85,      # confidence >= 85%
        'medium': 0.70,    # confidence >= 70%
        'low': 0.0,        # confidence >= 0%
    }
    
    # Automatic IP blocking configuration
    AUTO_BLOCK_ENABLED = os.getenv('AUTO_BLOCK_ENABLED', 'true').lower() == 'true'
    AUTO_BLOCK_THRESHOLD = 0.90  # Auto-block if confidence >= 90%
    AUTO_BLOCK_SEVERITY = ['critical', 'high']
    
    # Firewall Integration
    UFW_ENABLED = os.getenv('UFW_ENABLED', 'false').lower() == 'true'
    SNORT_ENABLED = os.getenv('SNORT_ENABLED', 'false').lower() == 'true'
    FIREWALL_COMMAND_TIMEOUT = 10  # seconds
    
    # Backup Configuration
    BACKUP_DIR = BASE_DIR / 'backups'
    BACKUP_RETENTION_DAYS = 30
    
    # Subscription Plans
    SUBSCRIPTION_PLANS = {
        'free_trial': {
            'name': 'Free Trial',
            'price': 0,
            'max_requests_per_minute': 10,
            'max_requests_per_month': 10000,
            'duration_days': 14,
        },
        'small_companies': {
            'name': 'Small Companies',
            'price': 44,
            'max_requests_per_minute': 100,
            'max_requests_per_month': 1000000,
        },
        'enterprise': {
            'name': 'Enterprise',
            'price': 149,
            'max_requests_per_minute': 1000,
            'max_requests_per_month': 10000000,
        },
    }
    
    # Email Configuration (for notifications)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@securecore.com')
    
    # Downloads Configuration
    DOWNLOADS_DIR = PROJECT_ROOT / 'downloads'
    CLIENT_SOFTWARE = {
        'linux': {
            'filename': 'securecore-client-linux-x64.tar.gz',
            'version': '1.0.0',
        },
        'windows': {
            'filename': 'securecore-client-windows-x64.zip',
            'version': '1.0.0',
        },
    }
    
    # Admin Configuration
    DEFAULT_ADMIN_EMAIL = os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@securecore.com')
    DEFAULT_ADMIN_PASSWORD = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123')  # Change immediately
    
    # Pagination
    DEFAULT_PAGE_SIZE = 15
    MAX_PAGE_SIZE = 100
    
    # Feature Flags
    FEATURES = {
        'websocket_inference': True,
        'firebase_notifications': FIREBASE_ENABLED,
        'auto_blocking': AUTO_BLOCK_ENABLED,
        'email_notifications': True,
        'sms_notifications': False,
        'webhook_notifications': True,
        'data_export': True,
        'advanced_analytics': True,
    }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = 'Lax'  # None requires Secure=True (HTTPS)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Require environment variables in production
    @classmethod
    def init_app(cls, app):
        """Initialize production settings"""
        Config.init_app(app)
        
        # Ensure critical security settings
        assert app.config['SECRET_KEY'] != 'dev-secret-key-CHANGE-IN-PRODUCTION', \
            'SECRET_KEY must be set in production'
        assert app.config['JWT_SECRET_KEY'] != app.config['SECRET_KEY'], \
            'JWT_SECRET_KEY should be different from SECRET_KEY'
        
        # Ensure database is not SQLite in production (recommend PostgreSQL)
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            app.logger.warning(
                'SQLite detected in production. Consider migrating to PostgreSQL for better performance.'
            )


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}


def get_config(config_name=None):
    """Get configuration object based on environment"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    return config.get(config_name, DevelopmentConfig)
