"""
Security Utilities
Role-based access control and sanitization
"""
from functools import wraps
from typing import Iterable, Optional, Union, Callable

from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import bleach

from app.models.user import User
from app.models.user_company_role import UserCompanyRole
from app.models.user_role import UserRole
from app.models.role import Role

def get_user_company_role(user_or_id: Union[User, int], company_id: Optional[int] = None) -> Optional[str]:
    """Return the role for a user within a company (PBAC).

    Falls back to the user's legacy `role` field when no mapping exists.
    """
    user = user_or_id if isinstance(user_or_id, User) else User.query.get(user_or_id)
    if not user:
        return None

    target_company_id = company_id or user.company_id
    if target_company_id is None:
        return user.role

    # Preferred: new users_roles mapping
    try:
        mapping = (
            UserRole.query.join(Role, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user.id, UserRole.company_id == target_company_id)
            .first()
        )
        if mapping is not None and mapping.role is not None:
            return mapping.role.name
    except Exception:
        # If tables don't exist yet, ignore and fall back.
        pass

    mapping = UserCompanyRole.query.filter_by(user_id=user.id, company_id=target_company_id).first()
    return mapping.role if mapping else user.role


def require_company_role(allowed_roles: Iterable[str], company_kw: Optional[str] = None):
    """Decorator enforcing company-scoped roles.

    Args:
        allowed_roles: iterable of role strings allowed to proceed.
        company_kw: optional kwarg name to pull company_id from route kwargs; defaults to user's company_id.
    """

    def decorator(fn: Callable):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'Unauthorized'}), 401

            company_id = kwargs.get(company_kw) if company_kw else None
            role = get_user_company_role(user, company_id)
            if role not in allowed_roles:
                import logging
                logging.getLogger(__name__).warning(f"Role mismatch: User {user.email} has company role '{role}', but allowed roles are {allowed_roles}")
                return jsonify({'error': 'Insufficient role'}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(fn):
    """Decorator to require admin role (company-scoped)."""
    return require_company_role({'admin'})(fn)


def require_admin(fn):
    """Decorator to require admin role (alias for admin_required)."""
    return require_company_role({'admin'})(fn)


def require_fully_privileged_or_admin(fn):
    """Decorator to require fully_privileged or admin role."""
    return require_company_role({'admin', 'fully_privileged'})(fn)


def check_user_role(user_or_id: Union[User, int], company_id: Optional[int] = None) -> Optional[str]:
    """
    Get the role of a user within a company.
    
    Args:
        user_or_id: User object or user ID
        company_id: Optional company ID (defaults to user's company)
    
    Returns:
        Role string (e.g., 'admin', 'fully_privileged', 'limited') or None
    """
    return get_user_company_role(user_or_id, company_id)

def user_required(fn):
    """Decorator to require normal user role (not admin)"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        # Global service-provider admin check.
        if not user or user.role == 'admin':
            return jsonify({'error': 'User access required'}), 403
        return fn(*args, **kwargs)
    return wrapper


def require_company_roles(allowed_roles):
    """Alias for require_company_role to keep naming consistent."""
    return require_company_role(allowed_roles)

def sanitize_html(text):
    """Sanitize HTML to prevent XSS"""
    if not text:
        return text
    # Strip all tags by default for simple text fields
    return bleach.clean(text, tags=[], attributes={}, strip=True)
