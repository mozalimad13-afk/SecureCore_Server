"""
Locations API Blueprint
Provides country listing for registration forms
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.location import Location
from app.models.location import companies_countries
from app.models.user import User

locations_bp = Blueprint('locations', __name__)

@locations_bp.route('/locations/countries', methods=['GET'])
def list_countries():
    # IMPORTANT: Public endpoint.
    # Registration needs to fetch countries before any user is logged in.
    # If a JWT is present, we can optionally scope to the user's company.
    user_id = None
    try:
        user_id = get_jwt_identity()
    except Exception:
        user_id = None

    company_id = None
    if user_id:
        user = User.query.get(user_id)
        company_id = user.company_id if user else None

    q = Location.query
    if company_id is not None:
        # If the company has explicit countries configured, return only those.
        # If none are configured, fall back to the global list.
        has_any = db.session.query(companies_countries.c.location_id).filter(
            companies_countries.c.company_id == company_id
        ).first()
        if has_any is not None:
            q = q.join(companies_countries, companies_countries.c.location_id == Location.id).filter(
                companies_countries.c.company_id == company_id
            )

    countries = q.order_by(Location.name.asc()).all()
    return jsonify({'countries': [c.to_dict() for c in countries]})
