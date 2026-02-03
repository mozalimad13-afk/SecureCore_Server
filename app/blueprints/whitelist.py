"""
Whitelist Blueprint
IP whitelist management for trusted IPs
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.utils.security import require_company_role
import logging

from app.models.whitelist import WhitelistedIP
from app.extensions import db
from app.models.user import User
from app.models.blocklist import BlockedIP

logger = logging.getLogger(__name__)

whitelist_bp = Blueprint('whitelist', __name__)


@whitelist_bp.route('', methods=['GET'])
@require_company_role({'admin', 'fully', 'limited'})
def get_whitelist():
    """
    Get user's whitelisted IPs with pagination
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
    query = WhitelistedIP.query.filter_by(company_id=user.company_id, is_active=True)
    
    # Apply search filter
    if search:
        query = query.filter(
            (WhitelistedIP.ip_address.like(f'%{search}%')) | 
            (WhitelistedIP.description.like(f'%{search}%'))
        )
    
    # Order by most recent
    query = query.order_by(WhitelistedIP.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'whitelisted_ips': [ip.to_dict() for ip in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next
        }
    }), 200


@whitelist_bp.route('', methods=['POST'])
@require_company_role({'admin', 'fully'})
def add_to_whitelist():
    """Add IP to whitelist"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    
    if 'ip_address' not in data:
        return jsonify({'error': 'IP address required'}), 400
    
    try:
        # Check if IP is blocked
        from app.models.blocklist import BlockedIP
        blocked = BlockedIP.query.filter_by(
            company_id=user.company_id,
            ip_address=data['ip_address'],
            is_active=True
        ).first()
        
        if blocked:
            return jsonify({'error': "You can't add this IP to the whitelist because it's already in the blocklist."}), 409
            
        # Check if IP already whitelisted
        existing = WhitelistedIP.query.filter_by(
            company_id=user.company_id,
            ip_address=data['ip_address'],
            is_active=True
        ).first()
        
        if existing:
            return jsonify({'error': f"IP address {data['ip_address']} is already in the whitelist."}), 409
        
        whitelisted_ip = WhitelistedIP(
            company_id=user.company_id,
            ip_address=data['ip_address'],
            description=data.get('description'),
            created_by=user_id
        )
        
        db.session.add(whitelisted_ip)
        db.session.commit()
        
        return jsonify({
            'message': 'IP whitelisted successfully',
            'whitelisted_ip': whitelisted_ip.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error whitelisting IP: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to whitelist IP'}), 500


@whitelist_bp.route('/<int:whitelist_id>', methods=['DELETE'])
@require_company_role({'admin', 'fully'})
def remove_from_whitelist(whitelist_id):
    """Remove IP from whitelist"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        whitelisted_ip = WhitelistedIP.query.filter_by(
            id=whitelist_id, company_id=user.company_id
        ).first()
        
        if not whitelisted_ip:
            return jsonify({'error': 'Whitelisted IP not found'}), 404
        
        whitelisted_ip.is_active = False
        from datetime import datetime
        whitelisted_ip.deactivated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'message': 'IP removed from whitelist'}), 200
        
    except Exception as e:
        logger.error(f"Error removing from whitelist: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to remove from whitelist'}), 500
@whitelist_bp.route('/<int:whitelist_id>', methods=['PATCH'])
@require_company_role({'admin', 'fully'})
def update_whitelist_entry(whitelist_id):
    """Update a whitelist entry (description)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    
    whitelisted_ip = WhitelistedIP.query.filter_by(
        id=whitelist_id, company_id=user.company_id, is_active=True
    ).first()
    
    if not whitelisted_ip:
        return jsonify({'error': 'Whitelist entry not found'}), 404
    
    if 'description' in data:
        whitelisted_ip.description = data['description']
        db.session.commit()
        return jsonify({'message': 'Whitelist entry updated', 'whitelisted_ip': whitelisted_ip.to_dict()}), 200
    
    return jsonify({'error': 'No updates provided'}), 400
