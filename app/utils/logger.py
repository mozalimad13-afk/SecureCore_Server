"""
Centralized Logging Configuration
Sets up rotating file handlers and formatters
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from config import Config


def setup_logging(app):
    """
    Configure application logging
    
    Args:
        app: Flask application instance
    """
    # Set log level
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Clear existing handlers
    app.logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    app.logger.addHandler(console_handler)
    
    # File handler for general logs
    if not app.config['TESTING']:
        file_handler = RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        app.logger.addHandler(file_handler)
        
        # Error log handler
        error_handler = RotatingFileHandler(
            Config.ERROR_LOG_FILE,
            maxBytes=Config.LOG_MAX_BYTES,
            backupCount=Config.LOG_BACKUP_COUNT
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        app.logger.addHandler(error_handler)
    
    # Set log level
    app.logger.setLevel(log_level)
    
    # Also configure root logger for other modules
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] %(levelname)s [%(name)s]: %(message)s'
    )
    
    app.logger.info(f"Logging configured - Level: {Config.LOG_LEVEL}")
