"""Firebase Service for Push Notifications.

Uses `firebase-admin` to send push notifications to registered devices.

Device tokens are stored encrypted at rest in `fcm_devices.device_token_encrypted`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import firebase_admin
from firebase_admin import credentials, messaging
from flask import has_app_context, current_app

from app.extensions import db
from app.models.fcm_device import FCMDevice
from app.utils.encryption import decrypt_fcm_token
from config import Config

logger = logging.getLogger(__name__)


class FirebaseService:
    """Firebase Cloud Messaging service for push notifications."""

    def __init__(self):
        self._app: Optional[firebase_admin.App] = None
        self.initialized = False
        self._init_error: Optional[str] = None
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Initialize firebase-admin once (best-effort)."""

        if self.initialized:
            return

        try:
            # Avoid double-initialization when reloader runs.
            try:
                existing = firebase_admin.get_app('securecore')
            except Exception:
                existing = None
            if existing is not None:
                self._app = existing
                self.initialized = True
                logger.info("Firebase service initialized (existing app)")
                return

            if has_app_context():
                cfg = current_app.config
                firebase_enabled = bool(cfg.get('FIREBASE_ENABLED', False))
                cred_path = Path(str(cfg.get('FIREBASE_CREDENTIALS_FILE', '')))
                project_id = cfg.get('FIREBASE_PROJECT_ID')
            else:
                firebase_enabled = bool(getattr(Config, 'FIREBASE_ENABLED', False))
                cred_path = Path(str(getattr(Config, 'FIREBASE_CREDENTIALS_FILE', '')))
                project_id = getattr(Config, 'FIREBASE_PROJECT_ID', None)

            if not firebase_enabled:
                self._init_error = 'disabled'
                logger.info("Firebase service disabled (FIREBASE_ENABLED=false)")
                return

            if not cred_path or not cred_path.exists():
                self._init_error = f"credentials file not found: {cred_path}"
                logger.warning(f"Firebase credentials file not found: {cred_path}")
                return

            cred = credentials.Certificate(str(cred_path))
            self._app = firebase_admin.initialize_app(
                cred,
                {
                    'projectId': project_id,
                },
                name='securecore',
            )
            self.initialized = True
            logger.info(f"Firebase service initialized using {cred_path}")
        except Exception as e:
            self._init_error = str(e)
            logger.exception("Failed to initialize Firebase service")

    def send_notification(self, user_id: int, title: str, body: str, data: dict | None = None) -> bool:
        """Send a push notification to all active devices for a user."""

        self._ensure_initialized()
        if not self.initialized or self._app is None:
            logger.info(f"Firebase send skipped (not initialized: {self._init_error})")
            return False

        # Collect plaintext tokens for active devices.
        devices = (
            db.session.query(FCMDevice)
            .filter(FCMDevice.user_id == user_id)
            .filter(FCMDevice.is_active.is_(True))
            .filter(FCMDevice.device_token_encrypted.isnot(None))
            .all()
        )

        tokens: list[str] = []
        for d in devices:
            try:
                token = decrypt_fcm_token(d.device_token_encrypted)
                if token:
                    tokens.append(token)
            except Exception:
                logger.exception(f"Failed to decrypt FCM token for device {d.id}")

        if not tokens:
            logger.info(f"No FCM tokens for user_id={user_id}")
            return False

        payload_data: dict[str, str] = {}
        if data:
            # FCM data payload must be strings.
            for k, v in data.items():
                if v is None:
                    continue
                payload_data[str(k)] = str(v)

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=payload_data or None,
            tokens=tokens,
        )

        try:
            resp = messaging.send_each_for_multicast(message, app=self._app)
            logger.info(
                f"Firebase multicast user_id={user_id} success={resp.success_count} failure={resp.failure_count}"
            )
            return resp.success_count > 0
        except Exception:
            logger.exception(f"Firebase send failed for user_id={user_id}")
            return False


# Global instance
_firebase_service = None


def get_firebase_service():
    """Get global Firebase service instance"""
    global _firebase_service
    if _firebase_service is None:
        _firebase_service = FirebaseService()
    return _firebase_service
