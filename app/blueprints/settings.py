"""
Settings Blueprint
Manages both company settings and user profile settings
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.security import require_admin
import logging
from datetime import datetime, timedelta

from app.models.company_settings import CompanySettings
from app.models.user_profile import UserProfile
from app.models.user import User
from app.models.alert import Alert
from app.models.blocklist import BlockedIP
from app.models.whitelist import WhitelistedIP
from app.extensions import db
from flask import current_app
import json
import sqlite3
import os

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)


# ============================================================================
# COMPANY SETTINGS (Admin only)
# ============================================================================

@settings_bp.route('/company', methods=['GET'])
@require_admin
def get_company_settings():
    """Get company settings (admin only)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    
    try:
        settings = CompanySettings.query.filter_by(company_id=user.company_id).first()
        
        if not settings:
            # Create default settings
            settings = CompanySettings(company_id=user.company_id)
            db.session.add(settings)
            db.session.commit()
        
        # Get subscription info
        from app.models.subscription import Subscription
        subscription = Subscription.query.filter_by(company_id=user.company_id).first()
        
        # Combine settings with subscription info
        settings_dict = settings.to_dict()
        if subscription:
            settings_dict.update({
                'plan': subscription.plan_name,
                'planPrice': str(subscription.plan_price),
                'nextBillingDate': subscription.next_billing_date.isoformat() if subscription.next_billing_date else None
            })
        else:
            settings_dict.update({
                'plan': 'Free Trial',
                'planPrice': '0',
                'nextBillingDate': None
            })
        
        return jsonify({'settings': settings_dict}), 200
        
    except Exception as e:
        logger.error(f"Error getting company settings: {str(e)}")
        return jsonify({'error': 'Failed to get company settings'}), 500


@settings_bp.route('/company', methods=['PUT'])
@require_admin
def update_company_settings():
    """Update company settings (admin only)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    data = request.get_json()
    
    try:
        settings = CompanySettings.query.filter_by(company_id=user.company_id).first()
        
        if not settings:
            settings = CompanySettings(company_id=user.company_id)
            db.session.add(settings)
        
        # Update notification settings
        if 'emailNotifications' in data:
            settings.email_notifications = data['emailNotifications']
        if 'smsNotifications' in data:
            settings.sms_notifications = data['smsNotifications']
        if 'webhookNotifications' in data:
            settings.webhook_notifications = data['webhookNotifications']
        if 'webhookUrl' in data:
            settings.webhook_url = data['webhookUrl']
        
        # Update digest settings
        if 'dailyDigest' in data:
            settings.daily_digest = data['dailyDigest']
        if 'weeklyReport' in data:
            settings.weekly_report = data['weeklyReport']
        if 'digestTime' in data:
            settings.digest_time = data['digestTime']
        
        # Update backup settings
        if 'backupFrequency' in data:
            settings.backup_frequency = data['backupFrequency']
        
        # Update reminder settings
        if 'alertReminderEnabled' in data:
            settings.alert_reminder_enabled = data['alertReminderEnabled']
        if 'alertReminderInterval' in data:
            settings.alert_reminder_interval = data['alertReminderInterval']
        
        settings.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Company settings updated successfully',
            'settings': settings.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating company settings: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update company settings'}), 500


@settings_bp.route('/company/backup/run', methods=['POST'])
@require_admin
def run_company_backup():
    """Trigger manual company backup (admin only)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    
    try:
        settings = CompanySettings.query.filter_by(company_id=user.company_id).first()
        
        if not settings:
            return jsonify({'error': 'Company settings not found'}), 404
        
        # Collect company data for backup
        alerts = Alert.query.filter_by(company_id=user.company_id).all()
        blocks = BlockedIP.query.filter_by(company_id=user.company_id).all()
        whitelists = WhitelistedIP.query.filter_by(company_id=user.company_id).all()
        company_users = User.query.filter_by(company_id=user.company_id).all()
        
        backup_data = {
            'company': {
                'id': user.company_id,
                'name': user.company.name if user.company else 'Unknown'
            },
            'users': [{'name': u.name, 'email': u.email, 'role': u.role} for u in company_users],
            'settings': settings.to_dict(),
            'alerts': [a.to_dict() for a in alerts],
            'blocked_ips': [b.to_dict() for b in blocks],
            'whitelisted_ips': [w.to_dict() for w in whitelists]
        }
        
        # Save backup to consolidated SQLite file
        backup_dir = current_app.config['BACKUP_DIR']
        backup_file = os.path.join(backup_dir, "all_backups.db")
        
        # Create/Update SQLite file with indexed table
        conn = sqlite3.connect(backup_file)
        c = conn.cursor()
        
        # Check if table exists with correct schema, drop if outdated
        try:
            c.execute('SELECT company_id FROM backup_data LIMIT 1')
        except sqlite3.OperationalError:
            # Table doesn't have company_id column, drop and recreate
            c.execute('DROP TABLE IF EXISTS backup_data')
        
        c.execute('CREATE TABLE IF NOT EXISTS backup_data (company_id INTEGER PRIMARY KEY, payload TEXT, created_at TEXT)')
        
        # Replace existing backup for this company in the consolidated file
        c.execute('INSERT OR REPLACE INTO backup_data (company_id, payload, created_at) VALUES (?, ?, ?)', 
                  (user.company_id, json.dumps(backup_data), datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        
        # Update backup timestamps
        settings.last_backup = datetime.utcnow()
        
        # Calculate next backup based on frequency
        if settings.backup_frequency == 'hourly':
            settings.next_backup = datetime.utcnow() + timedelta(hours=1)
        elif settings.backup_frequency == 'daily':
            settings.next_backup = datetime.utcnow() + timedelta(days=1)
        elif settings.backup_frequency == 'weekly':
            settings.next_backup = datetime.utcnow() + timedelta(weeks=1)
        elif settings.backup_frequency == 'monthly':
            settings.next_backup = datetime.utcnow() + timedelta(days=30)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Company backup completed successfully',
            'lastBackup': settings.last_backup.isoformat(),
            'nextBackup': settings.next_backup.isoformat() if settings.next_backup else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error running company backup: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Company backup failed'}), 500


# ============================================================================
# USER PROFILE (All authenticated users)
# ============================================================================

@settings_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_user_profile():
    """Get user profile settings"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if not profile:
            # Create default profile
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)
            db.session.commit()
        
        # Combine profile with user's basic info
        profile_dict = profile.to_dict()
        profile_dict.update({
            'name': user.name,
            'email': user.email,
            'country': user.country,
        })
        
        return jsonify({'profile': profile_dict}), 200
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({'error': 'Failed to get user profile'}), 500


@settings_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_user_profile():
    """Update user profile settings"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    try:
        # Update basic user info
        if 'name' in data:
            from app.utils.security import sanitize_html
            user.name = sanitize_html(data['name'])
        if 'country' in data:
            user.country = data['country']
        
        # Update password if provided
        if 'currentPassword' in data and 'newPassword' in data:
            if not user.check_password(data['currentPassword']):
                return jsonify({'error': 'Current password is incorrect'}), 400
            user.set_password(data['newPassword'])
        
        # Update user profile
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)
        
        if 'displayName' in data:
            profile.display_name = data['displayName']
        if 'bio' in data:
            profile.bio = data['bio']
        if 'timezone' in data:
            profile.timezone = data['timezone']
        if 'language' in data:
            profile.language = data['language']
        if 'theme' in data:
            profile.theme = data['theme']
        if 'emailOnMention' in data:
            profile.email_on_mention = data['emailOnMention']
        if 'emailOnAlert' in data:
            profile.email_on_alert = data['emailOnAlert']
        if 'pushNotifications' in data:
            profile.push_notifications = data['pushNotifications']
        
        profile.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': profile.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update user profile'}), 500


# ============================================================================
# LEGACY ENDPOINTS (for backward compatibility - will be deprecated)
# ============================================================================

@settings_bp.route('', methods=['GET'])
@jwt_required()
def get_settings_legacy():
    """
    Legacy endpoint - redirects to company settings for admins, profile for others
    DEPRECATED: Use /settings/company or /settings/profile instead
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    from app.utils.security import check_user_role
    role = check_user_role(user)
    
    # Admins get company settings, others get profile
    if role == 'admin':
        return get_company_settings()
    else:
        return get_user_profile()


@settings_bp.route('', methods=['PUT'])
@jwt_required()
def update_settings_legacy():
    """
    Legacy endpoint - redirects to company settings for admins, profile for others
    DEPRECATED: Use /settings/company or /settings/profile instead
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    from app.utils.security import check_user_role
    role = check_user_role(user)
    
    # Admins can update company settings, others update profile
    if role == 'admin':
        return update_company_settings()
    else:
        return update_user_profile()


@settings_bp.route('/backup/run', methods=['POST'])
@require_admin
def run_backup_legacy():
    """
    Legacy endpoint - redirects to company backup
    DEPRECATED: Use /settings/company/backup/run instead
    """
    return run_company_backup()
