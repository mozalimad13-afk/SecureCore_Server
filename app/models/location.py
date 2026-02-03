"""
Location Model
Stores countries for selection and association
"""
from app.extensions import db


companies_countries = db.Table(
    'companies_countries',
    db.Column('company_id', db.Integer, db.ForeignKey('companies.id', ondelete='CASCADE'), primary_key=True),
    db.Column('location_id', db.Integer, db.ForeignKey('locations.id', ondelete='CASCADE'), primary_key=True),
    db.UniqueConstraint('company_id', 'location_id', name='uq_company_location'),
)

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(2), nullable=False, index=True)  # ISO 3166-1 alpha-2
    name = db.Column(db.String(100), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('code', name='uq_location_code'),
        db.UniqueConstraint('name', name='uq_location_name'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
        }

class UserCountry(db.Model):
    __tablename__ = 'user_countries'  # many-to-many association
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id', ondelete='CASCADE'), nullable=False, index=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'location_id', name='uq_user_location'),
    )
