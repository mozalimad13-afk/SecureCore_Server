"""
Authentication API Blueprint
Handles user authentication, registration, and token management
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import logging
from datetime import datetime, timezone
import hashlib

from app.extensions import db, limiter
from app.models.user import User
from app.models.company import Company
from app.models.user_company_role import UserCompanyRole
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.payment_method import PaymentMethod
from app.models.token import APIToken
from app.models.notification import Notification
from app.models.fcm_device import FCMDevice
from app.middleware.csrf import get_new_csrf_token
from app.utils.encryption import encrypt_fcm_token
from config import Config

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
@limiter.limit(Config.RATE_LIMITS['auth_login'])
def login():
    """
    User login endpoint - Sets JWT in HttpOnly cookie
    
    Request:
        {
            "email": "user@example.com",
            "password": "password"
        }
    
    Response:
        {
            "csrf_token": "...",
            "user": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password required'}), 400
        
        email = data['email'].strip()
        password = data['password']
        device_id = (data.get('device_id') or '').strip() or None
        
        logger.debug(f"Login attempt for: '{email}'")
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            logger.warning(f"User not found: {email}")
            return jsonify({'error': 'Invalid credentials'}), 401
            
        if not user.check_password(password):
            logger.warning(f"Password mismatch for user: {email}")
            # Do NOT log the password, but we can log lengths for debugging
            logger.debug(f"Received password length: {len(password)}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            logger.warning(f"Inactive user login attempt: {email}")
            return jsonify({'error': 'Account is inactive'}), 403

        # If mobile provides a device_id, upsert a per-device record (encrypted at rest).
        # Mobile login contract is intentionally minimal: email + password + device_id.
        if device_id:
            try:
                if not user.company_id:
                    return jsonify({'error': 'Company not configured for user'}), 500

                device_id_hash = hashlib.sha256(device_id.encode('utf-8')).hexdigest()
                existing = FCMDevice.query.filter_by(
                    company_id=user.company_id,
                    user_id=user.id,
                    device_id_hash=device_id_hash,
                ).first()

                if existing is None:
                    existing = FCMDevice(
                        company_id=user.company_id,
                        user_id=user.id,
                        device_id_hash=device_id_hash,
                        device_id_encrypted=encrypt_fcm_token(device_id),
                        is_active=True,
                        last_seen_at=datetime.now(timezone.utc),
                    )
                    db.session.add(existing)
                else:
                    existing.is_active = True
                    existing.last_seen_at = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(f"Failed to upsert device for {email}: {str(e)}")
                db.session.rollback()
                return jsonify({'error': 'Login failed'}), 500
        
        # Update last login + any device upsert
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        
        # Create JWT tokens
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        # Generate CSRF token
        csrf_token = get_new_csrf_token(user_id=user.id)
        
        logger.info(f"User logged in: {email}")
        
        # Create response
        response = jsonify({
            'csrf_token': csrf_token,
            'user': user.to_dict()
        })
        
        # Set JWT in cookies using helper functions
        # This uses the app config (JWT_COOKIE_SECURE, JWT_COOKIE_SAMESITE, etc.)
        from flask_jwt_extended import set_access_cookies, set_refresh_cookies
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/register', methods=['POST'])
@limiter.limit(Config.RATE_LIMITS['auth_register'])
def register():
    """
    User registration endpoint
    
    Request:
        {
            "email": "user@example.com",
            "password": "password",
            "name": "User Name"
        }
    
    Response:
        {
            "message": "User registered successfully",
            "user": {...}
        }
    """
    try:
        data = request.get_json() or {}

        # Validate input
        required_fields = ['email', 'password', 'name']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        email = (data.get('email') or '').strip()
        password = data.get('password')
        name = (data.get('name') or '').strip()

        if not email or not password or not name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        # Create company (formerly tenant)
        company_name = (data.get('company') or '').strip() or name
        phone = (data.get('phone') or '').strip() or None

        # If a company name already exists, reuse it. This prevents accidental
        # duplicate companies when registering multiple users for same company.
        company = Company.query.filter_by(name=company_name).first()
        if company is None:
            company = Company(
                public_id=Company.generate_public_id(),
                name=company_name,
                company=company_name,
                phone_number=phone
            )
            db.session.add(company)
            db.session.flush()  # Get company.id
            
            # Create initial trial subscription
            from app.models.subscription import Subscription
            trial_sub = Subscription(
                company_id=company.id,
                plan_name='Free Trial',
                plan_price=0.0,
                status='trial'
            )
            db.session.add(trial_sub)

        # Create user
        user = User(
            company_id=company.id,
            email=email,
            name=name,
            role='user',
            is_active=True
        )
        user.set_password(password)
        # Optional country (string) from registration
        user.country = (data.get('country') or '').strip() or None
        
        db.session.add(user)
        db.session.flush()  # Flush to get user.id before adding payment method

        # Company-scoped role assignment.
        # Global `users.role` must remain 'user' (service-provider admin is separate).
        # Prefer the new roles/users_roles tables, but fall back to legacy mapping if
        # the migration hasn't been run yet.
        try:
            Role.__table__.create(db.engine, checkfirst=True)
            UserRole.__table__.create(db.engine, checkfirst=True)

            admin_role = Role.query.filter_by(name='admin').first()
            if admin_role is None:
                admin_role = Role(name='admin')
                db.session.add(admin_role)
                db.session.flush()

            db.session.add(UserRole(user_id=user.id, company_id=company.id, role_id=admin_role.id))
        except Exception:
            # Backward compatibility
            db.session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role='admin'))
        
        # Add payment method if provided
        if 'payment_data' in data:
            try:
                payment = data['payment_data']
                payment_method = PaymentMethod(
                    user_id=user.id,
                    card_last4=payment.get('card_number', '')[-4:],
                    card_brand='Card',  # Default, ideally detect from number
                    card_holder_name=payment.get('card_name', 'Unknown'),
                    expiry_month=payment.get('expiry_month', ''),
                    expiry_year=payment.get('expiry_year', ''),
                    billing_address=payment.get('billing_address'),
                    city=payment.get('city'),
                    zip_code=payment.get('zip_code'),
                    is_default=True,
                    is_active=True
                )
                db.session.add(payment_method)
            except Exception as e:
                logger.error(f"Failed to save payment info for user {email}: {str(e)}")
                # Continue with registration even if payment fails? 
                # For now, yes, but log it. Or we could rollback.
        
        # Link user to country record in locations (if present)
        try:
            from app.models.location import Location, UserCountry
            country_value = (data.get('country') or '').strip()
            if country_value:
                # Match by code or name (case-insensitive)
                loc = Location.query.filter(
                    (db.func.lower(Location.code) == country_value.lower())
                    | (db.func.lower(Location.name) == country_value.lower())
                ).first()
                if loc:
                    db.session.add(UserCountry(user_id=user.id, location_id=loc.id))
        except Exception as e:
            logger.warning(f"User country association failed for {email}: {str(e)}")
                
        db.session.commit()
        
        # Notify ONLY service provider admins (users.role == 'admin') about new registrations
        # NOT company users
        try:
            admins = User.query.filter(User.role == 'admin').all()
            for admin in admins:
                notification = Notification(
                    company_id=admin.company_id,
                    user_id=admin.id,
                    title='New User Registration',
                    message=f'New user registered: {name} ({email})',
                    type='info',
                    related_type='user_registration',
                    related_id=user.id,
                    link='/admin/users'
                )
                db.session.add(notification)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to notify service provider admins of registration: {str(e)}")
            
        logger.info(f"New user registered: {email}")
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint - Clears HttpOnly cookies"""
    try:
        user_id = get_jwt_identity()
        logger.info(f"User logged out: {user_id}")
        
        response = jsonify({'message': 'Logged out successfully'})
        
        # Clear cookies using helper
        from flask_jwt_extended import unset_jwt_cookies
        unset_jwt_cookies(response)
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500


@auth_bp.route('/me', methods=['GET', 'PUT'])
@jwt_required()
def handle_current_user():
    """Get or update current authenticated user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user is suspended
        if not user.is_active:
            logger.warning(f"Suspended user attempted to access account: {user.email}")
            return jsonify({'error': 'This user is suspended'}), 403
            
        if request.method == 'PUT':
            data = request.get_json()
            
            # Update name
            if 'name' in data:
                user.name = data['name']
            
            # Update email (check uniqueness)
            if 'email' in data and data['email'] != user.email:
                existing = User.query.filter_by(email=data['email']).first()
                if existing:
                    return jsonify({'error': 'Email already in use'}), 409
                user.email = data['email']
                
            # Update password
            if 'currentPassword' in data and 'newPassword' in data:
                if not user.check_password(data['currentPassword']):
                    return jsonify({'error': 'Invalid current password'}), 401
                user.set_password(data['newPassword'])
            
            db.session.commit()
            return jsonify({'message': 'Profile updated successfully', 'user': user.to_dict()}), 200
        
        # GET request
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"User operation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process user request'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    try:
        user_id = get_jwt_identity()
        
        # Verify user exists and is active
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_active:
            logger.warning(f"Suspended user attempted to refresh token: {user.email}")
            return jsonify({'error': 'This user is suspended'}), 403
        
        new_access_token = create_access_token(identity=user_id)
        
        # Generate new CSRF token
        csrf_token = get_new_csrf_token(user_id=user_id)
        
        # Create response
        response = jsonify({
            'csrf_token': csrf_token
        })
        
        # Set new access token in cookie
        from flask_jwt_extended import set_access_cookies
        set_access_cookies(response, new_access_token)
        
        return response, 200
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Token refresh failed'}), 500


@auth_bp.route('/csrf-token', methods=['GET'])
@jwt_required(optional=True)
def get_csrf_token():
    """Get a new CSRF token.

    Intended for browser clients using cookie-based JWT sessions.
    Mobile clients should use Bearer JWT and do not require CSRF.
    """
    try:
        user_id = None
        try:
            user_id = get_jwt_identity()
        except Exception:
            user_id = None

        csrf_token = get_new_csrf_token(user_id=user_id)
        return jsonify({'csrf_token': csrf_token}), 200

    except Exception as e:
        logger.error(f"CSRF token generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate CSRF token'}), 500
