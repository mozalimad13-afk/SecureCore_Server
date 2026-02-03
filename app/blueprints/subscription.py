from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.security import user_required, require_company_role
from app.utils.audit import log_audit
from app.models.subscription import Subscription
from app.extensions import db
from app.models.user import User

subscription_bp = Blueprint('subscription', __name__)

@subscription_bp.route('', methods=['GET'])
@user_required
def get_subscription():
    """Get user subscription"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    sub = Subscription.query.filter_by(company_id=user.company_id).first()
    
    if not sub:
        return jsonify({'subscription': None}), 200
        
    return jsonify({'subscription': sub.to_dict()}), 200


@subscription_bp.route('/cancel', methods=['POST'])
@require_company_role({'admin'})
def cancel_subscription():
    """Cancel user subscription"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    sub = Subscription.query.filter_by(company_id=user.company_id).first()
    
    if not sub:
        return jsonify({'error': 'Subscription not found'}), 404
        
    sub.plan_name = 'Cancelled'
    sub.status = 'cancelled'
    db.session.commit()
    
    log_audit(user_id, user.company_id, 'subscription_cancelled', 'subscription', sub.id, {'plan': sub.plan_name})

    return jsonify({
        'message': 'Subscription cancelled successfully',
        'subscription': sub.to_dict()
    }), 200


@subscription_bp.route('/resubscribe', methods=['POST'])
@require_company_role({'admin'})
def resubscribe():
    """Resubscribe user with a specific plan"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500
    data = request.get_json() or {}
    plan_name = data.get('plan', 'Small Companies')
    
    # Pricing logic
    plan_prices = {
        'Small Companies': 99.0,
        'Entropy': 499.0
    }
    price = plan_prices.get(plan_name, 99.0)
    
    sub = Subscription.query.filter_by(company_id=user.company_id).first()
    
    # Save payment method if card details provided
    from app.models.payment_method import PaymentMethod
    card_number = data.get('cardNumber')
    card_name = data.get('cardName')
    expiry = data.get('expiry', '') # Format "MM/YY"
    
    if card_number and card_name and expiry:
        # Extract last 4 and brand
        last4 = card_number[-4:]
        brand = 'Visa' # Simplified for now
    
    # The presence of 'card_last4' is used as an indicator that payment method details are provided
    if data.get('card_last4'):
        # Check if already exists (simplified to just adding new one)
        new_pm = PaymentMethod(
            company_id=user.company_id,
            card_last4=data.get('card_last4', '0000'),
            card_brand=data.get('card_brand', 'Visa'),
            card_holder_name=data.get('card_holder_name', user.name),
            expiry_month=data.get('expiry_month', '12'),
            expiry_year=data.get('expiry_year', '25'),
            is_default=True
        )
        
        # Unset other defaults
        PaymentMethod.query.filter_by(company_id=user.company_id).update({PaymentMethod.is_default: False})
        
        db.session.add(new_pm)
    
    if not sub:
        # If no subscription exists, create a new one
        sub = Subscription(company_id=user.company_id, plan_name=plan_name, plan_price=price, status='active')
        db.session.add(sub)
    else:
        sub.plan_name = plan_name
        sub.plan_price = price
        sub.status = 'active'
        
    db.session.commit()
    
    log_audit(user_id, user.company_id, 'subscription_resubscribed', 'subscription', sub.id, {'plan': plan_name, 'price': price})

    return jsonify({
        'message': f'Resubscribed to {plan_name} successfully',
        'subscription': sub.to_dict()
    }), 200
