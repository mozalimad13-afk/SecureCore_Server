"""
Database Initialization Script
Creates all database tables and initializes the database
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from app.extensions import db
from app.models import *  # Import all models
from config import Config


def init_database():
    """Initialize the database"""
    print("Initializing SecureCore IDS Database...")
    
    # Create app
    app = create_app('development')
    
    with app.app_context():
        # Drop all tables (careful in production!)
        print("Dropping existing tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating tables...")
        db.create_all()
        
        print("Database initialized successfully!")
        print(f"Database location: {Config.SQLALCHEMY_DATABASE_URI}")


if __name__ == '__main__':
    init_database()
