"""
Alerts API Blueprint
Handles alert retrieval, acknowledgment, and management
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from datetime import datetime, timedelta

from app.services.alert_service import AlertService
from app.models.user import User
from app.models.alert import Alert
from app.extensions import db

logger = logging.getLogger(__name__)

alerts_bp = Blueprint('alerts', __name__)
alert_service = AlertService()


@alerts_bp.route('', methods=['GET'])
@jwt_required()
def get_alerts():
    """
    Get alerts for current user with filtering and pagination
    
    Query params:
        page: Page number (default: 1)
        per_page: Items per page (default: 15)
        severity: Filter by severity
        attack_type: Filter by attack type
        acknowledged: Deprecated (no longer stored)
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        severity = request.args.get('severity')
        attack_type = request.args.get('attack_type')
        # No longer supported; kept for backward compatibility.
        acknowledged = None
        
        # Get alerts
        result = alert_service.get_user_alerts(
                user_id=user_id,
            company_id=user.company_id,
            page=page,
            per_page=per_page,
            severity=severity,
            attack_type=attack_type,
            acknowledged=acknowledged
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get alerts error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve alerts'}), 500


@alerts_bp.route('/<int:alert_id>', methods=['GET'])
@jwt_required()
def get_alert(alert_id):
    """Get a specific alert"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        
        from app.models.alert import Alert
        alert = Alert.query.filter_by(id=alert_id, company_id=user.company_id).first()
        
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        return jsonify({'alert': alert.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Get alert error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve alert'}), 500


@alerts_bp.route('/<int:alert_id>/acknowledge', methods=['PUT'])
@jwt_required()
def acknowledge_alert(alert_id):
    """Deprecated: alert acknowledgement state is no longer stored."""
    _ = alert_id
    # Keep status aligned with prior behavior (resource not available).
    return jsonify({'error': 'Alert not found'}), 404


@alerts_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_alert_stats():
    """
    Get alert statistics for dashboard
    Returns total alerts, blocked threats, severity distribution, etc.
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        
        time_range = request.args.get('time_range', 'today')  # Default to today for dashboard context
        
        # Calculate start date based on range
        now = datetime.utcnow()
        if time_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            trend_days = 7  # Still show last 7 days for trend unless specified
        elif time_range == '7d':
            start_date = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            trend_days = 7
        elif time_range == 'month':
            start_date = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            trend_days = 30
        elif time_range == 'quarter':
            start_date = (now - timedelta(days=90)).replace(hour=0, minute=0, second=0, microsecond=0)
            trend_days = 90
        elif time_range == 'year':
            start_date = (now - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)
            trend_days = 365
        else:  # 'all'
            start_date = datetime(2000, 1, 1)
            trend_days = 30 # Show last 30 days for trend in all-time view
            
        # Total alerts in range
        total_alerts = Alert.query.filter(
            Alert.company_id == user.company_id,
            Alert.created_at >= start_date
        ).count()
        
        # Blocked threats (total count from blocklist table)
        from app.models.blocklist import BlockedIP
        blocked_count = BlockedIP.query.filter_by(
            company_id=user.company_id,
            is_active=True
        ).count()
        
        # Severity distribution in range
        severity_counts = db.session.query(
            Alert.severity,
            db.func.count(Alert.id)
        ).filter(
            Alert.company_id == user.company_id,
            Alert.created_at >= start_date
        ).group_by(Alert.severity).all()
        
        severity_distribution = {
            'Low': 0,
            'Medium': 0,
            'High': 0,
            'Critical': 0
        }
        
        for severity, count in severity_counts:
            sev_key = severity.capitalize()
            if sev_key in severity_distribution:
                severity_distribution[sev_key] = count
        
        # Trend data
        trend_data = []
        if time_range == 'year' or time_range == 'all':
            # Group by month for last 12 months
            for i in range(12):
                month_date = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
                next_month = (month_date + timedelta(days=32)).replace(day=1)
                
                day_count = Alert.query.filter(
                    Alert.company_id == user.company_id,
                    Alert.created_at >= month_date,
                    Alert.created_at < next_month
                ).count()
                
                day_blocked = BlockedIP.query.filter(
                    BlockedIP.company_id == user.company_id,
                    BlockedIP.is_active == True,
                    BlockedIP.created_at >= month_date,
                    BlockedIP.created_at < next_month
                ).count()
                
                trend_data.insert(0, {
                    'date': month_date.strftime('%b'),
                    'alerts': day_count,
                    'blocked': day_blocked
                })
        elif time_range == 'quarter':
            # Group by week for last 12 weeks
            for i in range(12):
                week_start = (now - timedelta(days=now.weekday(), weeks=12-1-i)).replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = week_start + timedelta(days=7)
                
                day_count = Alert.query.filter(
                    Alert.company_id == user.company_id,
                    Alert.created_at >= week_start,
                    Alert.created_at < week_end
                ).count()
                
                day_blocked = BlockedIP.query.filter(
                    BlockedIP.company_id == user.company_id,
                    BlockedIP.is_active == True,
                    BlockedIP.created_at >= week_start,
                    BlockedIP.created_at < week_end
                ).count()
                
                trend_data.append({
                    'date': f"W{i+1}",
                    'alerts': day_count,
                    'blocked': day_blocked
                })
        else:
            # Daily or Hourly (default to 7-30 days daily)
            points = 7 if time_range in ['today', '7d'] else 30
            for i in range(points):
                day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=points-1-i)
                day_end = day_start + timedelta(days=1)
                
                day_count = Alert.query.filter(
                    Alert.company_id == user.company_id,
                    Alert.created_at >= day_start,
                    Alert.created_at < day_end
                ).count()
                
                day_blocked = BlockedIP.query.filter(
                    BlockedIP.company_id == user.company_id,
                    BlockedIP.is_active == True,
                    BlockedIP.created_at >= day_start,
                    BlockedIP.created_at < day_end
                ).count()
                
                trend_data.append({
                    'date': day_start.strftime('%d %b'),
                    'alerts': day_count,
                    'blocked': day_blocked
                })
        
        # Get system health status
        from app.utils.health import get_system_health
        system_health = get_system_health()
        
        return jsonify({
            'total_alerts': total_alerts,
            'total_today': total_alerts if time_range == 'today' else 0, # compatibility
            'blocked_threats': blocked_count,
            'severity_distribution': severity_distribution,
            'weekly_trend': trend_data,
            'system_status': system_health.get('overall_status', 'healthy')
        }), 200
        
    except Exception as e:
        logger.error(f"Get alert stats error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve alert statistics'}), 500


@alerts_bp.route('/recent', methods=['GET'])
@jwt_required()
def get_recent_alerts():
    """
    Get recent alerts for quick dashboard view
    Limited to last 5-10 alerts
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        limit = request.args.get('limit', 5, type=int)
        
        # Limit to max 20
        if limit > 20:
            limit = 20
        
        recent = Alert.query.filter_by(
            company_id=user.company_id
        ).order_by(
            Alert.created_at.desc()
        ).limit(limit).all()
        
        return jsonify({
            'recent_alerts': [alert.to_dict() for alert in recent]
        }), 200
        
    except Exception as e:
        logger.error(f"Get recent alerts error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve recent alerts'}), 500
