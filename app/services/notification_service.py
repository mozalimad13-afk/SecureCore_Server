"""
Notification Service
Handles in-app notifications
"""
import logging
from datetime import datetime

from app.extensions import db

logger = logging.getLogger(__name__)


class NotificationService:
    """Manages in-app notifications"""
    
    def create_notification(self, user_id, title, message, type='info',
                            priority='medium', related_alert_id=None, tenant_id=None):
        """
        Create a new notification
        
        Args:
            tenant_id: Tenant ID (recommended; required for tenant-scoped APIs)
            user_id: User ID to send notification to
            title: Notification title
            message: Notification message
            type: Notification type ('alert', 'info', 'warning', 'success')
            priority: Priority level
            related_alert_id: Optional related alert ID
        
        Returns:
            Notification: Created notification object
        """
        try:
            from app.models.notification import Notification
            
            notification = Notification(
                tenant_id=tenant_id,
                user_id=user_id,
                title=title,
                message=message,
                type=type,
                priority=priority,
                related_alert_id=related_alert_id,
                is_read=False
            )
            
            db.session.add(notification)
            db.session.commit()
            
            logger.info(f"Notification created for user {user_id}")
            return notification
            
        except Exception as e:
            logger.error(f"Failed to create notification: {str(e)}")
            db.session.rollback()
            return None


# Notification model would be similar to other models
# Create it in app/models/notification.py
