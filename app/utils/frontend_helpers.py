"""
Utility functions for frontend compatibility
Provides data transformation helpers for API responses
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional


def get_relative_time(dt: datetime) -> str:
    """
    Convert datetime to relative time string for frontend
    
    Examples:
        - "Just now"
        - "2 min ago"
        - "5 hours ago"
        - "3 days ago"
    """
    if not dt:
        return "Unknown"
    
    # Ensure timezone-aware datetime
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "Just now"
    
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes} min ago" if minutes > 1 else "1 min ago"
    
    hours = int(minutes / 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    
    days = int(hours / 24)
    if days < 7:
        return f"{days} day{'s' if days > 1 else ''} ago"
    
    weeks = int(days / 7)
    if weeks < 4:
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    
    months = int(days / 30)
    if months < 12:
        return f"{months} month{'s' if months > 1 else ''} ago"
    
    years = int(days / 365)
    return f"{years} year{'s' if years > 1 else ''} ago"


def format_datetime(dt: Optional[datetime], format_type: str = 'iso') -> Optional[str]:
    """
    Format datetime for frontend consumption
    
    Args:
        dt: datetime object
        format_type: 'iso', 'relative', or 'friendly'
    
    Returns:
        Formatted string or None
    """
    if not dt:
        return None
    
    if format_type == 'iso':
        return dt.isoformat()
    elif format_type == 'relative':
        return get_relative_time(dt)
    elif format_type == 'friendly':
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return dt.isoformat()


def format_ip_for_frontend(ip: str, include_port: bool = False) -> str:
    """Format IP address for frontend display"""
    if not ip:
        return "Unknown"
    return ip


def serialize_for_frontend(data: Any, include_relative_time: bool = True) -> Dict:
    """
    Serialize data with frontend-compatible formats
    
    Automatically converts:
    - datetime objects to ISO strings
    - Adds relative time fields
    - Handles None values
    """
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                result[key] = format_datetime(value, 'iso')
                if include_relative_time:
                    result[f"{key}_relative"] = get_relative_time(value)
            elif value is None:
                result[key] = None
            else:
                result[key] = value
        return result
    
    return data


def to_frontend_dict(obj: Any, include_meta: bool = False) -> Dict:
    """
    Convert SQLAlchemy model to frontend-compatible dict
    
    Args:
        obj: SQLAlchemy model instance
        include_meta: Include metadata like timestamps in relative format
    
    Returns:
        Dictionary with frontend-compatible formatting
    """
    if hasattr(obj, 'to_dict'):
        base_dict = obj.to_dict()
    else:
        base_dict = {}
    
    # Add relative time for common timestamp fields
    if include_meta:
        for time_field in ['created_at', 'updated_at', 'last_login', 'timestamp']:
            if hasattr(obj, time_field):
                dt = getattr(obj, time_field)
                if dt:
                    base_dict[f"{time_field}_relative"] = get_relative_time(dt)
    
    return base_dict


def paginate_response(items: list, page: int, per_page: int, total: int) -> Dict:
    """
    Create frontend-compatible pagination response
    
    Returns:
        {
            'items': [...],
            'pagination': {
                'page': 1,
                'per_page': 15,
                'total': 100,
                'pages': 7,
                'has_prev': False,
                'has_next': True
            }
        }
    """
    import math
    
    total_pages = math.ceil(total / per_page) if per_page > 0 else 0
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    }
