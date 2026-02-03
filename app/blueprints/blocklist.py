"""
Blocklist Blueprint
IP blocking management
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.utils.security import require_company_role
import logging

from app.services.firewall_service import FirewallService
from app.models.blocklist import BlockedIP
from app.models.user import User
from app.extensions import db

logger = logging.getLogger(__name__)

blocklist_bp = Blueprint('blocklist', __name__)
firewall_service = FirewallService()


@blocklist_bp.route('', methods=['GET'])
@require_company_role({'admin', 'fully', 'limited'})
def get_blocklist():
    """
    Get user's blocked IPs with pagination
    Supports: page, per_page, search
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)
    search = request.args.get('search', '', type=str)
    
    # Build query
    query = BlockedIP.query.filter_by(company_id=user.company_id, is_active=True)
    
    # Apply search filter
    if search:
        query = query.filter(
            (BlockedIP.ip_address.like(f'%{search}%')) | 
            (BlockedIP.reason.like(f'%{search}%'))
        )
    
    # Order by most recent
    query = query.order_by(BlockedIP.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'blocked_ips': [ip.to_dict() for ip in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        }
    }), 200


@blocklist_bp.route('', methods=['POST'])
@require_company_role({'admin', 'fully'})
def add_to_blocklist():
    """Block an IP address"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    
    if 'ip_address' not in data:
        return jsonify({'error': 'IP address required'}), 400
    
    try:
        # Check if IP is whitelisted
        from app.models.whitelist import WhitelistedIP
        whitelisted = WhitelistedIP.query.filter_by(
            company_id=user.company_id,
            ip_address=data['ip_address'],
            is_active=True
        ).first()
        
        if whitelisted:
            return jsonify({'error': "You can't add this IP to the blocklist because it's already in the whitelist."}), 409
            
        # Check if IP already blocked
        existing = BlockedIP.query.filter_by(
            company_id=user.company_id,
            ip_address=data['ip_address'],
            is_active=True
        ).first()
        
        if existing:
            return jsonify({'error': f"IP address {data['ip_address']} is already in the blocklist."}), 409
        
        success = firewall_service.block_ip(
            company_id=user.company_id,
            ip_address=data['ip_address'],
            reason=data.get('reason'),
            block_type='manual'
        )
        
        if success:
            return jsonify({'message': f"IP address {data['ip_address']} has been added to the blocklist."}), 201
        return jsonify({'error': 'Failed to block IP'}), 500
        
    except Exception as e:
        logger.error(f"Error blocking IP: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to block IP'}), 500


@blocklist_bp.route('/<int:blocked_ip_id>', methods=['DELETE'])
@require_company_role({'admin', 'fully'})
def remove_from_blocklist(blocked_ip_id):
    """Unblock an IP address"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    success = firewall_service.unblock_ip(blocked_ip_id, user.company_id)
    
    if success:
        return jsonify({'message': 'IP unblocked successfully'}), 200
    return jsonify({'error': 'Failed to unblock IP'}), 500
@blocklist_bp.route('/<int:blocked_ip_id>', methods=['PATCH'])
@require_company_role({'admin', 'fully'})
def update_blocklist_entry(blocked_ip_id):
    """Update a blocklist entry (reason)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    
    blocked_ip = BlockedIP.query.filter_by(
        id=blocked_ip_id, company_id=user.company_id, is_active=True
    ).first()
    
    if not blocked_ip:
        return jsonify({'error': 'Blocklist entry not found'}), 404
    
    if 'reason' in data:
        blocked_ip.reason = data['reason']
        db.session.commit()
        return jsonify({'message': 'Blocklist entry updated', 'blocked_ip': blocked_ip.to_dict()}), 200
    
    return jsonify({'error': 'No updates provided'}), 400
