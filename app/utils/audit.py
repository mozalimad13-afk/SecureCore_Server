"""Audit logging utilities for sensitive actions."""
from datetime import datetime
from typing import Optional, Any, Dict

from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), index=True, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), index=True, nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(100), nullable=False)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


def log_audit(user_id: Optional[int], company_id: Optional[int], action: str, resource_type: str, resource_id: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
    entry = AuditLog(
        user_id=user_id,
        company_id=company_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=metadata or {},
    )
    db.session.add(entry)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return entry
