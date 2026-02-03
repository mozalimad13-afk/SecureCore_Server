"""Company members management endpoints."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
import secrets

from app.extensions import db
from app.models.user import User
from app.models.user_company_role import UserCompanyRole
from app.models.role import Role
from app.models.user_role import UserRole
from app.utils.audit import log_audit
from app.utils.security import require_company_role, get_user_company_role, sanitize_html


members_bp = Blueprint('members', __name__)


def _member_to_dict(user: User) -> dict:
    return {
        **user.to_dict(),
        'company_role': get_user_company_role(user) or user.role,
    }


@members_bp.route('', methods=['GET'])
@require_company_role({'admin'})
def list_members():
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    company_id = current_user.company_id

    members = User.query.filter_by(company_id=company_id).all()
    return jsonify({'members': [_member_to_dict(m) for m in members]}), 200


@members_bp.route('', methods=['POST'])
@require_company_role({'admin'})
def create_member():
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    company_id = current_user.company_id

    data = request.get_json() or {}
    email = sanitize_html((data.get('email') or '').strip())
    name = sanitize_html((data.get('name') or '').strip())
    role = (data.get('role') or 'limited').strip() or 'limited'
    password = (data.get('password') or '').strip() or secrets.token_urlsafe(12)
    country = (data.get('country') or '').strip() or None

    if not email or not name:
        return jsonify({'error': 'email and name are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    member = User(
        company_id=company_id,
        email=email,
        name=name,
        role='user',
        is_active=True,
    )
    member.set_password(password)
    member.country = country
    db.session.add(member)
    db.session.flush()

    # Prefer new users_roles mapping; fallback to legacy mapping.
    try:
        Role.__table__.create(db.engine, checkfirst=True)
        UserRole.__table__.create(db.engine, checkfirst=True)

        role_obj = Role.query.filter_by(name=role).first()
        if role_obj is None:
            role_obj = Role(name=role)
            db.session.add(role_obj)
            db.session.flush()

        # Check if role assignment already exists to avoid UNIQUE constraint error
        existing_role = UserRole.query.filter_by(
            user_id=member.id, 
            company_id=company_id, 
            role_id=role_obj.id
        ).first()
        
        if not existing_role:
            db.session.add(UserRole(user_id=member.id, company_id=company_id, role_id=role_obj.id))
    except Exception:
        db.session.add(UserCompanyRole(user_id=member.id, company_id=company_id, role=role))
    db.session.commit()

    log_audit(user_id, company_id, 'member_created', 'user', member.id, {'role': role, 'email': email})

    return jsonify({'member': _member_to_dict(member)}), 201


@members_bp.route('/<int:member_id>/role', methods=['PATCH'])
@require_company_role({'admin'})
def update_member_role(member_id: int):
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    company_id = current_user.company_id

    target = User.query.get(member_id)
    if not target or target.company_id != company_id:
        return jsonify({'error': 'Member not found'}), 404

    data = request.get_json() or {}
    new_role = (data.get('role') or '').strip()
    if not new_role:
        return jsonify({'error': 'role is required'}), 400

    # Update company-scoped role mapping. Do not change global users.role.
    updated = False
    try:
        Role.__table__.create(db.engine, checkfirst=True)
        UserRole.__table__.create(db.engine, checkfirst=True)

        role_obj = Role.query.filter_by(name=new_role).first()
        if role_obj is None:
            role_obj = Role(name=new_role)
            db.session.add(role_obj)
            db.session.flush()

        existing = UserRole.query.filter_by(user_id=target.id, company_id=company_id).first()
        if existing:
            existing.role_id = role_obj.id
        else:
            db.session.add(UserRole(user_id=target.id, company_id=company_id, role_id=role_obj.id))
        updated = True
    except Exception:
        pass

    if not updated:
        mapping = UserCompanyRole.query.filter_by(user_id=target.id, company_id=company_id).first()
        if mapping:
            mapping.role = new_role
        else:
            db.session.add(UserCompanyRole(user_id=target.id, company_id=company_id, role=new_role))
    db.session.commit()

    log_audit(user_id, company_id, 'member_role_updated', 'user', target.id, {'new_role': new_role})

    return jsonify({'member': _member_to_dict(target)}), 200


@members_bp.route('/<int:member_id>/deactivate', methods=['POST'])
@require_company_role({'admin'})
def deactivate_member(member_id: int):
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    company_id = current_user.company_id

    target = User.query.get(member_id)
    if not target or target.company_id != company_id:
        return jsonify({'error': 'Member not found'}), 404

    target.is_active = False
    db.session.commit()

    log_audit(user_id, company_id, 'member_deactivated', 'user', target.id)

    return jsonify({'member': _member_to_dict(target)}), 200


@members_bp.route('/<int:member_id>/activate', methods=['POST'])
@require_company_role({'admin'})
def activate_member(member_id: int):
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    company_id = current_user.company_id

    target = User.query.get(member_id)
    if not target or target.company_id != company_id:
        return jsonify({'error': 'Member not found'}), 404

    target.is_active = True
    db.session.commit()

    log_audit(user_id, company_id, 'member_activated', 'user', target.id)

    return jsonify({'member': _member_to_dict(target)}), 200
