"""
Firewall Service
Integration with UFW and Snort for IP blocking
"""
import subprocess
import logging
from datetime import datetime

from app.extensions import db
from config import Config

logger = logging.getLogger(__name__)


class FirewallService:
    """Handles firewall operations (UFW/Snort integration)"""
    
    def __init__(self):
        """Initialize firewall service"""
        self.ufw_enabled = Config.UFW_ENABLED
        self.snort_enabled = Config.SNORT_ENABLED
        self.command_timeout = Config.FIREWALL_COMMAND_TIMEOUT
    
    def block_ip(self, company_id, ip_address, reason=None, related_alert_id=None,
                 block_type='manual'):
        """
        Block an IP address using UFW
        
        Args:
            company_id: Company ID
            ip_address: IP address to block
            reason: Optional reason for blocking
            related_alert_id: Optional alert ID that triggered the block
            block_type: 'manual', 'automatic', or 'temporary'
        
        Returns:
            bool: Success status
        """
        try:
            # Validate IP address
            if not self._validate_ip(ip_address):
                logger.error(f"Invalid IP address: {ip_address}")
                return False
            
            # Check if already blocked
            from app.models.blocklist import BlockedIP
            existing = BlockedIP.query.filter_by(
                company_id=company_id,
                ip_address=ip_address,
                is_active=True
            ).first()
            
            if existing:
                logger.warning(f"IP {ip_address} already blocked for company {company_id}")
                return True
            
            # Execute UFW block command
            if self.ufw_enabled:
                success, rule_number = self._execute_ufw_block(ip_address)
                if not success:
                    logger.error(f"UFW block failed for {ip_address}")
                    return False
            else:
                rule_number = None
            
            # Create database record
            blocked_ip = BlockedIP(
                company_id=company_id,
                ip_address=ip_address,
                reason=reason,
                related_alert_id=related_alert_id,
                block_type=block_type,
                is_active=True,
                ufw_rule_number=rule_number
            )
            
            db.session.add(blocked_ip)
            db.session.commit()
            
            logger.info(f"IP {ip_address} blocked successfully for company {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"Block IP failed: {str(e)}")
            db.session.rollback()
            return False
    
    def unblock_ip(self, blocked_ip_id, company_id):
        """
        Unblock an IP address
        
        Args:
            blocked_ip_id: Blocked IP record ID
            company_id: Company ID
        
        Returns:
            bool: Success status
        """
        try:
            from app.models.blocklist import BlockedIP
            blocked_ip = BlockedIP.query.filter_by(
                id=blocked_ip_id,
                company_id=company_id,
                is_active=True
            ).first()
            
            if not blocked_ip:
                logger.error(f"Blocked IP {blocked_ip_id} not found for company {company_id}")
                return False
            
            # Execute UFW unblock
            if self.ufw_enabled and blocked_ip.ufw_rule_number:
                self._execute_ufw_unblock(blocked_ip.ufw_rule_number)
            
            # Update database
            blocked_ip.is_active = False
            blocked_ip.deactivated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"IP {blocked_ip.ip_address} unblocked for company {company_id}")
            return True
            
        except Exception as e:
            logger.error(f"Unblock IP failed: {str(e)}")
            db.session.rollback()
            return False
    
    def _validate_ip(self, ip_address):
        """Validate IP address format"""
        import ipaddress
        try:
            ipaddress.ip_address(ip_address)
            return True
        except ValueError:
            return False
    
    def _execute_ufw_block(self, ip_address):
        """
        Execute UFW command to block IP
        
        Args:
            ip_address: IP to block
        
        Returns:
            tuple: (success: bool, rule_number: int or None)
        """
        try:
            # UFW command: sudo ufw deny from <ip>
            # In production, use a dedicated user with sudo privileges for this specific command
            command = ['sudo', 'ufw', 'deny', 'from', ip_address]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.command_timeout
            )
            
            if result.returncode == 0:
                logger.info(f"UFW block command executed successfully for {ip_address}")
                # Extract rule number from output (if available)
                # This depends on UFW output format
                return True, None
            else:
                logger.error(f"UFW block command failed: {result.stderr}")
                return False, None
                
        except subprocess.TimeoutExpired:
            logger.error(f"UFW command timed out for {ip_address}")
            return False, None
        except Exception as e:
            logger.error(f"UFW command execution error: {str(e)}")
            return False, None
    
    def _execute_ufw_unblock(self, rule_number):
        """Execute UFW command to unblock IP"""
        try:
            # UFW command: sudo ufw delete <rule_number>
            command = ['sudo', 'ufw', 'delete', str(rule_number)]
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.command_timeout
            )
            
            if result.returncode == 0:
                logger.info(f"UFW unblock command executed successfully")
                return True
            else:
                logger.error(f"UFW unblock command failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"UFW unblock error: {str(e)}")
            return False


# Note: Additional BlockedIP and WhitelistedIP models need to be created
# Similar structure to other models
