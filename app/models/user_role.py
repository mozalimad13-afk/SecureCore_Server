"""User-role mapping for PBAC.

Many-to-many between users and companies via roles.
"""

from datetime import datetime

from app.extensions import db


class UserRole(db.Model):
    __tablename__ = 'users_roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'company_id', 'role_id', name='uq_user_company_role_id'),
    )

    role = db.relationship('Role')

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'company_id': self.company_id,
            'role': self.role.name if self.role else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
