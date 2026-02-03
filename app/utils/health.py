"""
System Health Monitoring
Provides health metrics for admin dashboard
"""
import psutil
import platform
import os
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health metrics
    
    Returns health information for:
    - VPS/Server hardware
    - API server status
    - Database
    - Application
    """
    try:
        health_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'server': get_server_health(),
            'api': get_api_health(),
            'database': get_database_health(),
            'application': get_application_health()
        }
        
        # Calculate overall status
        statuses = [
            health_data['server']['status'],
            health_data['api']['status'],
            health_data['database']['status'],
            health_data['application']['status']
        ]
        
        if all(s == 'healthy' for s in statuses):
            health_data['overall_status'] = 'healthy'
        elif any(s == 'critical' for s in statuses):
            health_data['overall_status'] = 'critical'
        else:
            health_data['overall_status'] = 'degraded'
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            'overall_status': 'error',
            'error': str(e)
        }


def get_server_health() -> Dict[str, Any]:
    """Get VPS/Server hardware metrics"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Determine status based on thresholds
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            status = 'critical'
        elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 80:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'cpu': {
                'usage_percent': round(cpu_percent, 2),
                'cores': psutil.cpu_count(),
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            },
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'usage_percent': round(memory.percent, 2)
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'usage_percent': round(disk.percent, 2)
            },
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'architecture': platform.machine()
            }
        }
    except Exception as e:
        logger.error(f"Server health check error: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def get_api_health() -> Dict[str, Any]:
    """Get API server status"""
    try:
        # Check if Flask app is running
        from flask import current_app
        
        uptime_seconds = 0  # Would need to track app start time
        
        return {
            'status': 'healthy',
            'flask_version': current_app.config.get('FLASK_VERSION', 'unknown'),
            'environment': current_app.config.get('ENV', 'production'),
            'debug_mode': current_app.debug,
            'uptime_seconds': uptime_seconds,
            'endpoints_count': len([rule for rule in current_app.url_map.iter_rules()])
        }
    except Exception as e:
        logger.error(f"API health check error: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def get_database_health() -> Dict[str, Any]:
    """Get database status"""
    try:
        from app.extensions import db
        
        # Try a simple query
        db.session.execute(db.text('SELECT 1'))
        
        # Get database size (SQLite specific)
        db_path = db.engine.url.database
        if db_path and os.path.exists(db_path):
            db_size_mb = round(os.path.getsize(db_path) / (1024**2), 2)
        else:
            db_size_mb = 0
        
        # Count tables
        from app.models import User, Alert, APIToken, BlockedIP, WhitelistedIP
        
        table_counts = {
            'users': User.query.count(),
            'alerts': Alert.query.count(),
            'api_tokens': APIToken.query.filter_by(is_active=True).filter(APIToken.last_used_at.isnot(None)).count(),
            'blocked_ips': BlockedIP.query.count(),
            'whitelisted_ips': WhitelistedIP.query.count()
        }
        
        return {
            'status': 'healthy',
            'database_type': db.engine.name,
            'database_size_mb': db_size_mb,
            'table_counts': table_counts,
            'total_records': sum(table_counts.values())
        }
    except Exception as e:
        logger.error(f"Database health check error: {str(e)}")
        return {'status': 'critical', 'error': str(e)}


def get_application_health() -> Dict[str, Any]:
    """Get application-specific health metrics"""
    try:
        # Check critical services
        ml_status = 'operational'  # Would check if ML models loaded
        websocket_status = 'operational'  # Would check WebSocket server
        
        return {
            'status': 'healthy',
            'ml_inference': ml_status,
            'websocket_server': websocket_status,
            'python_version': platform.python_version(),
            'process_id': os.getpid()
        }
    except Exception as e:
        logger.error(f"Application health check error: {str(e)}")
        return {'status': 'error', 'error': str(e)}
