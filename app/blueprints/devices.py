"""
Devices API Blueprint
Registers per-device identifiers and (optionally) FCM tokens.

Stores `device_id` encrypted at rest using existing AES util.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models.fcm_device import FCMDevice
from app.models.user import User
from app.utils.encryption import encrypt_fcm_token

logger = logging.getLogger(__name__)

devices_bp = Blueprint('devices', __name__)


@devices_bp.route('', methods=['POST'])
@jwt_required()
def register_device():
    """Register or update a device for the current user.

    Body:
      {
        "device_id": "string" (required),
        "device_token": "string" (optional),
        "device_name": "string" (optional),
        "device_type": "android"|"ios"|"web" (optional),
        "device_platform": "string" (optional),
        "app_version": "string" (optional)
      }

    Notes:
    - `device_id` is stored encrypted (BLOB).
    - If `device_token` is not provided, we still register the device.
    """

    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user or not user.company_id:
        return jsonify({'error': 'Company not configured for user'}), 500

    data = request.get_json(silent=True) or {}
    device_id = (data.get('device_id') or '').strip()
    if not device_id:
        return jsonify({'error': 'device_id is required'}), 400

    device_token = (data.get('device_token') or '').strip() or None

    # Encrypt device_id using the existing AES helper.
    # The helper name is FCM-specific, but it is generic AES encryption.
    device_id_encrypted = encrypt_fcm_token(device_id)

    device_id_hash = hashlib.sha256(device_id.encode('utf-8')).hexdigest()

    q = FCMDevice.query.filter_by(user_id=user.id, company_id=user.company_id)
    existing = q.filter(FCMDevice.device_id_hash == device_id_hash).first()

    if existing is None:
        existing = FCMDevice(
            user_id=user.id,
            company_id=user.company_id,
            device_id_hash=device_id_hash,
            device_id_encrypted=device_id_encrypted,
        )
        db.session.add(existing)

    # Update metadata
    existing.device_name = data.get('device_name') or existing.device_name
    existing.device_type = data.get('device_type') or existing.device_type
    existing.device_platform = data.get('device_platform') or existing.device_platform
    existing.app_version = data.get('app_version') or existing.app_version
    existing.last_seen_at = datetime.now(timezone.utc)
    existing.is_active = True

    # Update token if provided
    if device_token is not None:
        existing.device_token_encrypted = encrypt_fcm_token(device_token)

    db.session.commit()

    return jsonify({'device': existing.to_dict()}), 200
