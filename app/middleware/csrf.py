"""
CSRF Protection Middleware
Implements token-based CSRF protection with rotation on every request
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, g, current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import logging

from app.extensions import db
from app.models.csrf_token import CSRFToken
from config import Config

logger = logging.getLogger(__name__)


def _as_utc_aware(value: datetime | None) -> datetime | None:
    """Normalize datetimes to timezone-aware UTC.

    SQLAlchemy/SQLite may return naive datetimes. To prevent runtime errors when
    mixing naive and aware values, treat naive timestamps as UTC.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def generate_csrf_token():
    """Generate a new CSRF token"""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def init_csrf_protection(app):
    """Initialize CSRF protection for the app"""
    
    @app.after_request
    def attach_csrf_token(response):
        """Include a new CSRF token in every state-changing response"""
        # We only strictly rotate on state-changing methods
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return response
            
        # Don't rotate if the response wasn't a success (optional, but safer to always rotate)
        if response.status_code >= 400:
            return response

        try:
            # Try to get user identity for the token
            user_id = None
            try:
                # Use verify_jwt_in_request(optional=True) to avoid throwing if not authenticated
                # but it might have been verified already in the view
                user_id = get_jwt_identity()
            except:
                pass
                
            token = get_new_csrf_token(user_id=user_id)
            if token:
                response.headers['X-CSRF-Token'] = token
                # For compatibility with frontend expecting it in body, 
                # we only use headers here to be clean.
        except Exception as e:
            logger.error(f"CSRF rotation error: {str(e)}")
            
        return response

    @app.before_request
    def csrf_protect():
        """CSRF protection middleware"""
        # Skip CSRF for safe methods
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return None
        
        # Skip CSRF for WebSocket connections
        if request.path.startswith('/ws/'):
            return None
        
        # Skip CSRF for health check
        if request.path == '/health':
            return None
        
        # Skip CSRF for auth endpoints (login, register, csrf-token)
        # These don't have an existing session to protect
        if request.path in ['/api/v1/auth/login', '/api/v1/auth/register', '/api/v1/auth/csrf-token']:
            return None

        # Skip CSRF for bearer-token requests (mobile/agents).
        # CSRF primarily protects cookie-auth (ambient authority). Bearer tokens are explicit.
        authz = request.headers.get('Authorization', '')
        if authz.lower().startswith('bearer '):
            return None

        # If there's a cookie-based JWT identity, bind the CSRF token to it.
        cookie_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            cookie_user_id = get_jwt_identity()
        except Exception:
            cookie_user_id = None
        
        # Get token from header
        token = request.headers.get('X-CSRF-Token')
        
        if not token:
            logger.warning(f"CSRF token missing from {request.remote_addr}")
            return jsonify({'error': 'CSRF token required'}), 403
        
        # Validate token
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        csrf_token = CSRFToken.query.filter_by(
            token_hash=token_hash,
            is_used=False
        ).first()

        # If authenticated via cookie JWT, the token must belong to that user.
        if cookie_user_id is not None and csrf_token and csrf_token.user_id != cookie_user_id:
            logger.warning(f"CSRF token user mismatch from {request.remote_addr}")
            return jsonify({'error': 'Invalid CSRF token'}), 403
        
        if not csrf_token:
            logger.warning(f"Invalid CSRF token from {request.remote_addr}")
            return jsonify({'error': 'Invalid CSRF token'}), 403
        
        # Check expiration (handle naive datetimes from DB)
        expires_at = _as_utc_aware(csrf_token.expires_at)
        if expires_at is not None and expires_at < datetime.now(timezone.utc):
            logger.warning(f"Expired CSRF token from {request.remote_addr}")
            return jsonify({'error': 'CSRF token expired'}), 403
        
        # Mark token as used
        csrf_token.is_used = True
        db.session.commit()
        
        return None
    
    logger.info("CSRF protection initialized")


def get_new_csrf_token(user_id=None, session_id=None):
    """
    Generate and store a new CSRF token
    
    Args:
        user_id: Optional user ID
        session_id: Optional session ID
    
    Returns:
        str: CSRF token to send to client
    """
    try:
        token, token_hash = generate_csrf_token()
        
        # Create CSRF token record
        csrf_token = CSRFToken(
            token_hash=token_hash,
            user_id=user_id,
            session_id=session_id,
            expires_at=datetime.now(timezone.utc) + Config.CSRF_TOKEN_EXPIRY
        )
        
        db.session.add(csrf_token)
        db.session.commit()
        
        return token
        
    except Exception as e:
        logger.error(f"Failed to create CSRF token: {str(e)}")
        db.session.rollback()
        return None


def cleanup_expired_tokens():
    """Clean up expired CSRF tokens (run periodically)"""
    try:
        deleted = CSRFToken.query.filter(
            CSRFToken.expires_at < datetime.now(timezone.utc)
        ).delete()
        
        db.session.commit()
        logger.info(f"Cleaned up {deleted} expired CSRF tokens")
        return deleted
        
    except Exception as e:
        logger.error(f"CSRF cleanup failed: {str(e)}")
        db.session.rollback()
        return 0
