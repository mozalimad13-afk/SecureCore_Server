"""Member deletion endpoint (company-scoped).

Split into a separate file to keep the original members blueprint minimal.
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models.user import User
from app.utils.audit import log_audit
from app.utils.security import require_company_role


members_delete_bp = Blueprint('members_delete', __name__)


@members_delete_bp.route('/<int:member_id>', methods=['DELETE'])
@require_company_role({'admin'})
def delete_member(member_id: int):
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    company_id = current_user.company_id

    target = User.query.get(member_id)
    if not target or target.company_id != company_id:
        return jsonify({'error': 'Member not found'}), 404

    if target.id == current_user.id:
        return jsonify({'error': 'Cannot delete yourself'}), 400

    db.session.delete(target)
    db.session.commit()

    log_audit(user_id, company_id, 'member_deleted', 'user', member_id)

    return jsonify({'message': 'Member deleted'}), 200
