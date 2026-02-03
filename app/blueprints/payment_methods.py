"""
Payment Methods API Blueprint
Handles payment method CRUD operations
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.security import require_admin
import logging

from app.extensions import db
from app.models.payment_method import PaymentMethod
from app.models.user import User

logger = logging.getLogger(__name__)

payment_methods_bp = Blueprint('payment_methods', __name__)


@payment_methods_bp.route('/payment-methods', methods=['GET'])
@require_admin
def get_payment_methods():
    """
    Get all active payment methods for current user
    
    Response:
        {
            "payment_methods": [
                {
                    "id": 1,
                    "card_last4": "4242",
                    "card_holder_name": "John Doe",
                    "expiry": "12/25",
                    "is_default": true,
                    ...
                }
            ]
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        
        methods = PaymentMethod.query.filter_by(
            company_id=user.company_id,
            is_active=True
        ).order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
        
        return jsonify({
            'payment_methods': [method.to_dict() for method in methods]
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching payment methods: {str(e)}")
        return jsonify({'error': 'Failed to fetch payment methods'}), 500


@payment_methods_bp.route('/payment-methods', methods=['POST'])
@require_admin
def add_payment_method():
    """
    Add a new payment method
    
    Request:
        {
            "card_number": "4242424242424242",  # Only last 4 stored
            "card_holder_name": "John Doe",
            "expiry_month": "12",
            "expiry_year": "25",
            "billing_address": "123 Main St",
            "city": "San Francisco",
            "zip_code": "94102",
            "country": "USA"
        }
    
    Response:
        {
            "payment_method": {...}
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['card_number', 'card_holder_name', 'expiry_month', 'expiry_year']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Extract last 4 digits only
        card_number = data['card_number'].replace(' ', '').replace('-', '')
        card_last4 = card_number[-4:]
        
        # Determine card brand (simple detection)
        card_brand = 'Unknown'
        if card_number.startswith('4'):
            card_brand = 'Visa'
        elif card_number.startswith(('51', '52', '53', '54', '55')):
            card_brand = 'Mastercard'
        elif card_number.startswith(('34', '37')):
            card_brand = 'Amex'
        
        # If this is the first payment method, make it default
        existing_methods = PaymentMethod.query.filter_by(company_id=user.company_id, is_active=True).count()
        is_default = existing_methods == 0
        
        # Create payment method
        payment_method = PaymentMethod(
            company_id=user.company_id,
            card_last4=card_last4,
            card_brand=card_brand,
            card_holder_name=data['card_holder_name'],
            expiry_month=data['expiry_month'],
            expiry_year=data['expiry_year'],
            billing_address=data.get('billing_address'),
            city=data.get('city'),
            zip_code=data.get('zip_code'),
            is_default=is_default
        )
        
        db.session.add(payment_method)
        db.session.commit()
        
        logger.info(f"Payment method added for user {user_id}")
        
        return jsonify({
            'payment_method': payment_method.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error adding payment method: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add payment method'}), 500


@payment_methods_bp.route('/payment-methods/<int:id>', methods=['DELETE'])
@require_admin
def delete_payment_method(id):
    """
    Delete (soft delete) a payment method
    
    Response:
        {
            "message": "Payment method deleted"
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        
        payment_method = PaymentMethod.query.filter_by(
            id=id,
            company_id=user.company_id,
            is_active=True
        ).first()
        
        if not payment_method:
            return jsonify({'error': 'Payment method not found'}), 404
        
        # Soft delete
        payment_method.is_active = False
        
        # If this was default, set another as default
        if payment_method.is_default:
            next_method = PaymentMethod.query.filter_by(
                company_id=user.company_id,
                is_active=True
            ).filter(PaymentMethod.id != id).first()
            
            if next_method:
                next_method.is_default = True
        
        db.session.commit()
        
        logger.info(f"Payment method {id} deleted for user {user_id}")
        
        return jsonify({'message': 'Payment method deleted'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting payment method: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete payment method'}), 500


@payment_methods_bp.route('/payment-methods/<int:id>/default', methods=['PUT'])
@require_admin
def set_default_payment_method(id):
    """
    Set a payment method as default
    
    Response:
        {
            "message": "Default payment method updated"
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or not user.company_id:
            return jsonify({'error': 'Company not configured for user'}), 500
        
        # Find the payment method
        payment_method = PaymentMethod.query.filter_by(
            id=id,
            company_id=user.company_id,
            is_active=True
        ).first()
        
        if not payment_method:
            return jsonify({'error': 'Payment method not found'}), 404
        
        # Unset current default
        PaymentMethod.query.filter_by(
            company_id=user.company_id,
            is_default=True
        ).update({'is_default': False})
        
        # Set new default
        payment_method.is_default = True
        
        db.session.commit()
        
        logger.info(f"Payment method {id} set as default for user {user_id}")
        
        return jsonify({'message': 'Default payment method updated'}), 200
        
    except Exception as e:
        logger.error(f"Error setting default payment method: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to set default payment method'}), 500
