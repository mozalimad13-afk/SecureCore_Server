"""
Centralized Error Handler
Handles all application errors with secure error responses
Never exposes stack traces in production
"""
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
import logging
import traceback

from config import Config

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register error handlers for the application"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors"""
        logger.warning(f"Bad request from {request.remote_addr}: {str(error)}")
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized errors"""
        logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden errors"""
        logger.warning(f"Forbidden access attempt from {request.remote_addr}")
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors"""
        return jsonify({
            'error': 'Not Found',
            'message': 'Resource not found'
        }), 404
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit errors"""
        logger.warning(f"Rate limit exceeded for {request.remote_addr}")
        return jsonify({
            'error': 'Rate Limit Exceeded',
            'message': 'Too many requests. Please try again later.'
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        logger.error(
            f"Internal error: {str(error)}\n"
            f"Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"IP: {request.remote_addr}"
        )
        
        # Log stack trace in debug mode only
        if app.config['DEBUG']:
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
        
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        """Handle database errors"""
        logger.error(f"Database error: {str(error)}")
        
        # Log details but don't expose to client
        if app.config['DEBUG']:
            logger.error(f"Details: {traceback.format_exc()}")
        
        return jsonify({
            'error': 'Database Error',
            'message': 'A database error occurred'
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle generic HTTP exceptions"""
        logger.warning(f"HTTP exception {error.code}: {str(error)}")
        return jsonify({
            'error': error.name,
            'message': error.description
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        logger.critical(
            f"Unexpected error: {str(error)}\n"
            f"Type: {type(error).__name__}\n"
            f"Path: {request.path}\n"
            f"Stack trace:\n{traceback.format_exc()}"
        )
        
        # Never expose internal errors in production
        if app.config['DEBUG']:
            message = str(error)
        else:
            message = 'An unexpected error occurred'
        
        return jsonify({
            'error': 'Unexpected Error',
            'message': message
        }), 500
    
    logger.info("Error handlers registered")
