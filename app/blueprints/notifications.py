"""
Notifications Blueprint
In-app notification management
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity
import logging

from app.models.notification import Notification
from app.extensions import db
from app.utils.security import require_company_role

logger = logging.getLogger(__name__)

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('', methods=['GET'])
@require_company_role({'admin', 'full', 'limited'})
def get_notifications():
    """Get user notifications"""
    user_id = get_jwt_identity()
    from app.models.user import User
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    
    # Get all notifications for this user
    # System health and registration notifications are only sent to service provider admins
    # so no need to filter here
    notifications = Notification.query.filter_by(
        company_id=user.company_id,
        user_id=user_id
    ).order_by(Notification.created_at.desc()).all()
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifications]
    }), 200


@notifications_bp.route('/<int:notification_id>/read', methods=['PUT'])
@require_company_role({'admin', 'full', 'limited'})
def mark_as_read(notification_id):
    """Mark notification as read"""
    user_id = get_jwt_identity()
    from app.models.user import User
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    
    notification = Notification.query.filter_by(
        id=notification_id, company_id=user.company_id, user_id=user_id
    ).first()
    
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404
    
    notification.is_read = True
    from datetime import datetime
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Notification marked as read'}), 200


@notifications_bp.route('/read-all', methods=['PUT'])
@require_company_role({'admin', 'full', 'limited'})
def mark_all_as_read():
    """Mark all notifications as read"""
    user_id = get_jwt_identity()
    from app.models.user import User
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    
    from datetime import datetime
    Notification.query.filter_by(
        company_id=user.company_id,
        user_id=user_id,
        is_read=False
    ).update({'is_read': True, 'read_at': datetime.utcnow()})
    
    db.session.commit()
    
    return jsonify({'message': 'All notifications marked as read'}), 200
@notifications_bp.route('', methods=['DELETE'])
@require_company_role({'admin', 'full'})
def clear_all_notifications():
    """Clear all notifications for the user"""
    user_id = get_jwt_identity()
    from app.models.user import User
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500

    Notification.query.filter_by(company_id=user.company_id, user_id=user_id).delete()
    db.session.commit()
    
    return jsonify({'message': 'All notifications cleared'}), 200
