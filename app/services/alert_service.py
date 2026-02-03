"""
Alert Service
Business logic for creating and managing security alerts
"""
import logging
from datetime import datetime
import json

from app.extensions import db
from app.models.alert import Alert
from app.services.firewall_service import FirewallService
from config import Config

logger = logging.getLogger(__name__)


class AlertService:
    """Handles alert creation, processing, and management"""
    
    def __init__(self):
        """Initialize alert service"""
        self.firewall_service = FirewallService()
    
    def create_alert(self, alert_data):
        """
        Create a new alert
        
        Args:
            alert_data: dict with alert information
        
        Returns:
            Alert: Created alert object
        """
        try:
            alert = Alert(
                company_id=alert_data.get('company_id') or alert_data.get('tenant_id'),
                source_ip=alert_data.get('source_ip', 'unknown'),
                source_port=alert_data.get('source_port'),
                destination_ip=alert_data.get('destination_ip'),
                destination_port=alert_data.get('destination_port'),
                protocol=alert_data.get('protocol'),
                attack_type=alert_data['attack_type'],
                severity=alert_data['severity'],
                confidence=alert_data['confidence'],
                raw_features=alert_data.get('raw_features'),
            )
            
            db.session.add(alert)
            db.session.commit()
            
            # Check if auto-blocking should be triggered
            if self._should_auto_block(alert):
                self._trigger_auto_block(alert)
            
            logger.info(f"Alert created: {alert.id}")
            return alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {str(e)}")
            db.session.rollback()
            raise
    
    def _should_auto_block(self, alert):
        """Determine if IP should be auto-blocked"""
        if not Config.AUTO_BLOCK_ENABLED:
            return False
        
        if alert.severity not in Config.AUTO_BLOCK_SEVERITY:
            return False
        
        if alert.confidence < Config.AUTO_BLOCK_THRESHOLD:
            return False
        
        return True
    
    def _trigger_auto_block(self, alert):
        """Trigger automatic IP blocking"""
        try:
            logger.info(f"Auto-blocking IP {alert.source_ip} for alert {alert.id}")
            
            success = self.firewall_service.block_ip(
                company_id=alert.company_id,
                ip_address=alert.source_ip,
                reason=f"Auto-blocked: {alert.attack_type}",
                related_alert_id=alert.id,
                block_type='automatic'
            )
            
            if success:
                logger.info(f"IP {alert.source_ip} auto-blocked successfully")
            else:
                logger.warning(f"Failed to auto-block IP {alert.source_ip}")
                
        except Exception as e:
            logger.error(f"Auto-block failed: {str(e)}")
    
    def get_user_alerts(self, user_id, company_id=None, page=1, per_page=15, severity=None,
                        attack_type=None, acknowledged=None):
        """
        Get alerts for a user with filtering and pagination
        
        Args:
            user_id: User ID (deprecated, kept for compatibility)
            company_id: Company ID to filter by
            page: Page number
            per_page: Items per page
            severity: Filter by severity
            attack_type: Filter by attack type
            acknowledged: Filter by acknowledged status
        
        Returns:
            dict: Paginated alerts
        """
        # Alerts are company-scoped, not user-scoped
        if company_id is None:
            raise ValueError("company_id is required")
        
        query = Alert.query.filter_by(company_id=company_id)
        
        if severity:
            query = query.filter_by(severity=severity)
        if attack_type:
            query = query.filter_by(attack_type=attack_type)
        # Acknowledgement state is no longer stored on Alert.
        _ = acknowledged
        
        # Order by newest first
        query = query.order_by(Alert.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'alerts': [alert.to_dict() for alert in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    

