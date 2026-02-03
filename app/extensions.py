"""
Flask Extensions Initialization
Centralized initialization of all Flask extensions
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Database
db = SQLAlchemy()
migrate = Migrate()

# JWT Authentication
jwt = JWTManager()

# Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri="memory://",  # Use Redis in production
)
