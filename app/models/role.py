"""Role model.

Defines the set of allowed company-scoped permissions.
"""

from datetime import datetime

from app.extensions import db


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'
