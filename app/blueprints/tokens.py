"""
API Tokens Blueprint
Manages API token generation, viewing, and revocation
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.security import require_admin
import logging

from app.models.token import APIToken
from app.extensions import db
from app.models.user import User
from app.utils.audit import log_audit

logger = logging.getLogger(__name__)

tokens_bp = Blueprint('tokens', __name__)


@tokens_bp.route('', methods=['GET'])
@require_admin
def get_tokens():
    """Get user's API tokens"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 400
    tokens = APIToken.query.filter_by(company_id=user.company_id, is_active=True).all()
    return jsonify({'tokens': [token.to_dict() for token in tokens]}), 200


@tokens_bp.route('/generate', methods=['POST'])
@require_admin
def generate_token():
    """Generate new API token (revokes existing tokens first)"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 400
    
    # Check subscription status - restricted if suspended
    from app.models.subscription import Subscription
    sub = Subscription.query.filter_by(company_id=user.company_id).first()
    if sub and sub.status == 'suspended':
        return jsonify({'error': 'Subscription suspended. Please update your payment method.'}), 403

    data = request.get_json() or {}
    
    # ENFORCE ONE TOKEN PER USER: Delete all existing tokens
    existing_tokens = APIToken.query.filter_by(company_id=user.company_id).all()
    for existing_token in existing_tokens:
        db.session.delete(existing_token)
        logger.info(f"Deleted token {existing_token.id} for user {user_id} during regeneration")
    
    # Generate new token
    token_string, token_hash, token_prefix = APIToken.generate_token()
    
    token = APIToken(
        company_id=user.company_id,
        token_hash=token_hash,
        token_prefix=token_prefix,
        name=data.get('name', 'API Token')
    )
    db.session.add(token)
    db.session.commit()
    log_audit(user_id, user.company_id, 'token_generated', 'api_token', token.id, {'name': token.name})
    
    logger.info(f"Generated new token {token.id} for user {user_id}")
    
    return jsonify({
        'message': 'Token generated successfully',
        'token': token_string,
        'token_info': token.to_dict()
    }), 201


@tokens_bp.route('/<int:token_id>', methods=['DELETE'])
@require_admin
def revoke_token(token_id):
    """Revoke API token"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 400
    token = APIToken.query.filter_by(id=token_id, company_id=user.company_id).first()
    
    if not token:
        return jsonify({'error': 'Token not found'}), 404
    
    token.is_active = False
    db.session.commit()
    log_audit(user_id, user.company_id, 'token_revoked', 'api_token', token.id)
    
    return jsonify({'message': 'Token revoked successfully'}), 200


@tokens_bp.route('/usage', methods=['GET'])
@require_admin
def get_usage():
    """Get token usage statistics"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 400
    tokens = APIToken.query.filter_by(company_id=user.company_id, is_active=True).all()
    
    return jsonify({
        'total_requests_today': sum(t.requests_today for t in tokens),
        'active_tokens': len(tokens),
        'tokens': [token.to_dict() for token in tokens]
    }), 200
