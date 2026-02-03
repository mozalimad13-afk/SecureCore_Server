"""
Admin Blueprint
Administrative operations
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
import logging

from app.models.user import User
from app.utils.security import get_user_company_role
from app.models.alert import Alert
from app.models.subscription import Subscription
from app.models.company import Company
from app.models.payment_method import PaymentMethod
from app.models.notification import Notification
from app.models.broadcast import AdminBroadcast
from app.extensions import db
from app.utils.security import admin_required
from app.services.firebase_service import get_firebase_service

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


def _plan_to_price(plan_name: str) -> float:
    plan_prices = {
        'Free': 0.0,
        'Small Companies': 99.0,
        'Enterprise': 499.0,
    }
    return float(plan_prices.get(plan_name, 0.0))


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get companies for admin UI (legacy route name).

    Frontend currently calls `/api/v1/admin/users` but the data is now company-owned.
    This endpoint returns a company list with subscription, alerts_count, and members.
    Excludes the admin's own company from the list.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)

    # Get current admin's company to exclude it from results
    admin_id = get_jwt_identity()
    admin_user = User.query.get(admin_id)
    admin_company_id = admin_user.company_id if admin_user else None

    # Query companies, excluding admin's own company
    query = Company.query
    if admin_company_id:
        query = query.filter(Company.id != admin_company_id)
    
    companies_paged = query.order_by(Company.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    company_ids = [c.id for c in companies_paged.items]

    # Aggregate alert counts per company.
    alerts_by_company: dict[int, int] = {}
    if company_ids:
        alerts_by_company = dict(
            db.session.query(Alert.company_id, db.func.count(Alert.id))
            .filter(Alert.company_id.in_(company_ids))
            .group_by(Alert.company_id)
            .all()
        )

    # Preload subscription per company.
    subs_by_company: dict[int, Subscription] = {}
    if company_ids:
        subs_by_company = {s.company_id: s for s in Subscription.query.filter(Subscription.company_id.in_(company_ids)).all()}

    pay_by_company: dict[int, PaymentMethod] = {}
    if company_ids:
        methods = PaymentMethod.query.filter(
            PaymentMethod.company_id.in_(company_ids),
            PaymentMethod.is_active.is_(True),
        ).order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
        for m in methods:
            if m.company_id not in pay_by_company:
                pay_by_company[m.company_id] = m

    companies_data = []
    for company in companies_paged.items:
        cd = company.to_dict()
        cd['alerts_count'] = alerts_by_company.get(company.id, 0)

        sub = subs_by_company.get(company.id)
        cd['subscription'] = {
            'plan': sub.plan_name,
            'status': sub.status,
            'expires_at': sub.end_date.isoformat() if sub.end_date else None,
        } if sub else None

        members = [u.to_dict() for u in (company.users or [])]
        # Add company role to each member
        for member in members:
            member_user = next((u for u in company.users if u.id == member['id']), None)
            if member_user:
                member['company_role'] = get_user_company_role(member_user, company.id)
        cd['members'] = members
        cd['members_count'] = len(members)

        pm = pay_by_company.get(company.id)
        cd['payment_info'] = pm.to_dict() if pm else None

        companies_data.append(cd)
    
    return jsonify({
        'users': companies_data,
        'pagination': {
            'total': companies_paged.total,
            'page': page,
            'per_page': per_page,
            'pages': companies_paged.pages
        }
    }), 200


@admin_bp.route('/companies/<int:company_id>', methods=['GET'])
@admin_required
def get_company_details(company_id: int):
    """Get details for a single company including linked users."""
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    cd = company.to_dict()
    cd['alerts_count'] = Alert.query.filter_by(company_id=company.id).count()

    sub = Subscription.query.filter_by(company_id=company.id).first()
    cd['subscription'] = {
        'plan': sub.plan_name,
        'status': sub.status,
        'expires_at': sub.end_date.isoformat() if sub.end_date else None,
    } if sub else None

    cd['members'] = [u.to_dict() for u in (company.users or [])]
    cd['members_count'] = len(cd['members'])

    pm = PaymentMethod.query.filter_by(company_id=company.id, is_active=True).order_by(
        PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()
    ).first()
    cd['payment_info'] = pm.to_dict() if pm else None
    return jsonify({'company': cd}), 200


@admin_bp.route('/companies/<int:company_id>/subscription', methods=['PUT'])
@admin_required
def set_company_subscription(company_id: int):
    """Set (or create) a company subscription plan.

    Body: {"plan": "Free"|"Small Companies"|"Enterprise"}
    """
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    data = request.get_json() or {}
    plan = data.get('plan')
    if plan not in {'Free', 'Small Companies', 'Enterprise'}:
        return jsonify({'error': 'Invalid plan'}), 400

    sub = Subscription.query.filter_by(company_id=company.id).first()
    if plan == 'Free':
        if not sub:
            # Create a free trial record if none exists
            sub = Subscription(company_id=company.id, plan_name='Free', plan_price=0.0, status='trial')
            db.session.add(sub)
        else:
            sub.plan_name = 'Free'
            sub.plan_price = 0.0
            sub.status = 'trial'
        db.session.commit()
        return jsonify({'subscription': sub.to_dict()}), 200

    price = _plan_to_price(plan)
    if not sub:
        sub = Subscription(company_id=company.id, plan_name=plan, plan_price=price, status='active')
        db.session.add(sub)
    else:
        sub.plan_name = plan
        sub.plan_price = price
        sub.status = 'active'
    db.session.commit()

    return jsonify({'subscription': {
        'plan': sub.plan_name,
        'status': sub.status,
        'expires_at': sub.end_date.isoformat() if sub.end_date else None,
    }}), 200


@admin_bp.route('/companies/<int:company_id>/subscription/cancel', methods=['POST'])
@admin_required
def cancel_company_subscription(company_id: int):
    """Cancel a company subscription, delete API tokens, and set to Free plan."""
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'error': 'Company not found'}), 404

    sub = Subscription.query.filter_by(company_id=company.id).first()
    
    # Keep API tokens but they will be blocked by subscription status check in WebSocket
    deleted_tokens = 0
    
    # Update the subscription record status to 'cancelled'
    if sub:
        sub.status = 'cancelled'
        sub.plan_name = 'Cancelled'
    
    db.session.commit()
    
    logger.info(f"Cancelled subscription for company {company_id}, deleted {deleted_tokens} API tokens")
    
    # Return Free plan with trial status
    return jsonify({
        'subscription': {
            'plan': 'Free',
            'status': 'trial',
            'expires_at': None,
        },
        'tokens_deleted': deleted_tokens
    }), 200


@admin_bp.route('/users/<int:user_id>/suspend', methods=['PUT'])
@admin_required
def suspend_user(user_id):
    """Suspend user account (admin can suspend any user)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'User suspended successfully'}), 200


@admin_bp.route('/health', methods=['GET'])
@jwt_required()
def get_system_health():
    """
    Get comprehensive system health metrics
    Admin only endpoint for monitoring server, API, database, and application
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or get_user_company_role(user) != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        from app.utils.health import get_system_health
        health_data = get_system_health()
        
        return jsonify(health_data), 200
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({'error': 'Health check failed'}), 500


@admin_bp.route('/users/<int:user_id>/activate', methods=['PUT'])
@admin_required
def activate_user(user_id):
    """Activate user account (admin can activate any user)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.is_active = True
    db.session.commit()
    
    return jsonify({'message': 'User activated successfully'}), 200


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id: int):
    """Update a user (admin can update any user).

    Body supports: name, email, role, password
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json() or {}

    try:
        if 'name' in data and data['name']:
            user.name = data['name']
        if 'email' in data and data['email']:
            # Only update email if it's different to avoid UNIQUE constraint error
            if data['email'] != user.email:
                # Check if email is already taken by another user
                existing = User.query.filter_by(email=data['email']).first()
                if existing and existing.id != user.id:
                    return jsonify({'error': f"Email '{data['email']}' is already taken by another user"}), 400
                user.email = data['email']
        if 'role' in data and data['role'] in {'user', 'admin'}:
            user.role = data['role']
        if 'password' in data and data['password']:
            user.set_password(data['password'])

        db.session.commit()
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        if 'UNIQUE constraint failed: users.email' in str(e):
            return jsonify({'error': f"Email '{data.get('email')}' is already in use"}), 400
        return jsonify({'error': 'Failed to update user'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id: int):
    """Delete a user (admin can delete any user)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200


@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    """Get admin dashboard statistics (excludes admin's own company)"""
    # Get current admin's company to exclude it from stats
    admin_id = get_jwt_identity()
    admin_user = User.query.get(admin_id)
    admin_company_id = admin_user.company_id if admin_user else None
    
    # Count companies excluding admin's own
    total_companies_query = Company.query
    if admin_company_id:
        total_companies_query = total_companies_query.filter(Company.id != admin_company_id)
    total_companies = total_companies_query.count()
    
    # Count alerts excluding admin's company
    total_alerts_query = Alert.query
    if admin_company_id:
        total_alerts_query = total_alerts_query.filter(Alert.company_id != admin_company_id)
    total_alerts = total_alerts_query.count()
    
    # Count active subscriptions excluding admin's company
    active_subscriptions_query = Subscription.query.filter_by(status='active')
    if admin_company_id:
        active_subscriptions_query = active_subscriptions_query.filter(Subscription.company_id != admin_company_id)
    active_subscriptions = active_subscriptions_query.count()
    
    # Calculate revenue trend and company growth
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    revenue_trend = []
    company_growth = []
    
    # Generate last 7 months of data
    for i in range(6, -1, -1):
        month_date = now - timedelta(days=i*30)
        month_name = month_date.strftime('%b')
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Count companies created up to this month (excluding admin's company)
        month_companies_query = Company.query.filter(Company.created_at <= month_date)
        if admin_company_id:
            month_companies_query = month_companies_query.filter(Company.id != admin_company_id)
        month_companies = month_companies_query.count()
        
        # Calculate revenue based on active subscriptions (excluding admin's)
        subs_query = Subscription.query.filter_by(status='active')
        if admin_company_id:
            subs_query = subs_query.filter(Subscription.company_id != admin_company_id)
        subs = subs_query.all()
        month_revenue = sum(sub.plan_price for sub in subs) if subs else 0
        
        revenue_trend.append({'month': month_name, 'revenue': month_revenue})
        company_growth.append({'month': month_name, 'companies': month_companies})
        
    return jsonify({
        'total_companies': total_companies,
        'total_alerts': total_alerts,
        'active_subscriptions': active_subscriptions,
        'system_load': 0,
        'company_growth': company_growth,
        'revenue_trend': revenue_trend
    }), 200
@admin_bp.route('/notifications/send', methods=['POST'])
@admin_required
def send_notification():
    """Send notification to all, single, or selected users"""
    data = request.get_json()
    if not data or not data.get('title') or not data.get('message'):
        return jsonify({'error': 'Title and message are required'}), 400
    
    target_type = data.get('target_type', 'all')  # 'all', 'single', 'selected'
    target_ids = data.get('target_ids', [])
    
    sender_id = get_jwt_identity()
    sender = User.query.get(sender_id)
    if not sender:
        return jsonify({'error': 'Unauthorized'}), 401
    count = 0
    
    # Identify recipients
    if target_type == 'all':
        recipients = User.query.filter_by(role='user').all()
    elif target_type == 'single' or target_type == 'selected':
        if not target_ids:
            return jsonify({'error': 'Recipient IDs required'}), 400
        recipients = User.query.filter(User.id.in_(target_ids)).all()
    else:
        return jsonify({'error': 'Invalid target type'}), 400

    if not recipients:
        return jsonify({'error': 'No valid recipients found'}), 400
    
    # Create notifications
    created_notifications = []
    for recipient in recipients:
        n = Notification(
            company_id=recipient.company_id,
            user_id=recipient.id,
            title=data['title'],
            message=data['message'],
            type='info',
            related_type='admin_broadcast'
        )
        db.session.add(n)
        created_notifications.append((recipient, n))
        count += 1

    # Derive a human-friendly target label for admin history
    if target_type == 'all':
        target_label = 'all'
    elif len(recipients) == 1:
        target_label = recipients[0].name or recipients[0].email
    else:
        target_label = f"multi {[u.name or u.email for u in recipients]}"
    
    # Log broadcast
    broadcast = AdminBroadcast(
        company_id=sender.company_id,
        sender_id=sender_id,
        title=data['title'],
        message=data['message'],
        target_type=target_label,
        recipient_count=count
    )
    db.session.add(broadcast)
    db.session.commit()

    # Best-effort realtime push to connected recipients
    # IMPORTANT: emit via the Socket.IO instance attached to the running Flask app.
    # Importing `socketio` from an entrypoint module can create a *second* Socket.IO
    # instance (and even a second Flask app) when this module is imported.
    try:
        from flask import current_app
        socketio = current_app.extensions.get('socketio')
        if socketio is None:
            raise RuntimeError('Socket.IO is not initialized on current_app')
        for recipient, n in created_notifications:
            payload = {
                'id': getattr(n, 'id', None),
                'title': getattr(n, 'title', None),
                'message': getattr(n, 'message', None),
                'type': getattr(n, 'type', 'alert'),
                'created_at': getattr(n, 'created_at', None).isoformat() if getattr(n, 'created_at', None) else None,
                'is_read': getattr(n, 'is_read', False),
            }
            socketio.emit(
                'notification_created',
                payload,
                room=f"company_{recipient.company_id}:user_{recipient.id}",
                namespace='/ws/ui'
            )
            
            # Mobile push via Firebase (best-effort)
            try:
                from app.services.firebase_service import get_firebase_service
                firebase_service = get_firebase_service()
                firebase_service.send_notification(
                    user_id=recipient.id,
                    title=data['title'],
                    body=data['message'],
                    data={
                        'type': 'admin_broadcast',
                        'title': data['title'],
                    }
                )
            except Exception:
                logger.warning(f"Failed to send Firebase push for admin broadcast to user {recipient.id}")
    except Exception:
        logger.exception('Failed to emit admin broadcast notifications')
    
    return jsonify({'message': f'Notification sent to {count} users'}), 201


@admin_bp.route('/notifications/history', methods=['GET'])
@admin_required
def get_notification_history():
    """Get history of notifications sent by admins"""
    admin_id = get_jwt_identity()
    admin_user = User.query.get(admin_id)
    if not admin_user or not admin_user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500

    broadcasts = AdminBroadcast.query.filter_by(
        company_id=admin_user.company_id
    ).order_by(AdminBroadcast.sent_at.desc()).all()
    return jsonify({
        'history': [b.to_dict() for b in broadcasts]
    }), 200


@admin_bp.route('/roles', methods=['GET'])
@admin_required
def get_roles():
    """Get available company roles for role management."""
    from app.models.role import Role
    from app.models.user_company_role import UserCompanyRole
    
    # Try to get roles from roles table (new schema)
    try:
        roles = Role.query.all()
        if roles:
            return jsonify({
                'roles': [role.name for role in roles]
            }), 200
    except Exception:
        pass
    
    # Fallback: get unique roles from user_company_roles (legacy)
    try:
        unique_roles = db.session.query(UserCompanyRole.role).distinct().all()
        role_names = [r[0] for r in unique_roles if r[0]]
    except Exception:
        # Default roles if tables don't exist
        role_names = ['admin', 'full', 'limited']
    
    return jsonify({
        'roles': role_names if role_names else ['admin', 'full', 'limited']
    }), 200


@admin_bp.route('/users/<int:user_id>/company-role', methods=['PUT'])
@admin_required
def update_user_company_role(user_id: int):
    """Update a user's company role."""
    from app.models.user_company_role import UserCompanyRole
    from app.models.user_role import UserRole
    from app.models.role import Role
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if not user.company_id:
        return jsonify({'error': 'User has no company'}), 400
    
    data = request.get_json() or {}
    new_role = data.get('role', '').strip()
    
    if not new_role:
        return jsonify({'error': 'Role is required'}), 400
    
    # Validate role exists
    valid_roles = ['admin', 'full', 'limited']  # Default valid roles
    try:
        roles = Role.query.all()
        if roles:
            valid_roles = [r.name for r in roles]
    except Exception:
        pass
    
    if new_role not in valid_roles:
        return jsonify({'error': f'Invalid role. Must be one of: {valid_roles}'}), 400
    
    try:
        # Try new users_roles table first
        try:
            role_obj = Role.query.filter_by(name=new_role).first()
            if not role_obj:
                role_obj = Role(name=new_role)
                db.session.add(role_obj)
                db.session.flush()
            
            user_role = UserRole.query.filter_by(
                user_id=user.id,
                company_id=user.company_id
            ).first()
            
            if user_role:
                user_role.role_id = role_obj.id
            else:
                user_role = UserRole(
                    user_id=user.id,
                    company_id=user.company_id,
                    role_id=role_obj.id
                )
                db.session.add(user_role)
        except Exception:
            # Fallback to legacy user_company_roles table
            ucr = UserCompanyRole.query.filter_by(
                user_id=user.id,
                company_id=user.company_id
            ).first()
            
            if ucr:
                ucr.role = new_role
            else:
                ucr = UserCompanyRole(
                    user_id=user.id,
                    company_id=user.company_id,
                    role=new_role
                )
                db.session.add(ucr)
        
        db.session.commit()
        logger.info(f"Updated role for user {user_id} to {new_role}")
        
        return jsonify({
            'message': 'User role updated successfully',
            'user_id': user_id,
            'role': new_role
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update user role: {str(e)}")
        return jsonify({'error': 'Failed to update user role'}), 500
