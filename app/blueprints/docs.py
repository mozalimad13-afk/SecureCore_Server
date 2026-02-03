"""
API Documentation Blueprint
Serves static HTML documentation from frontend
"""
from flask import Blueprint, jsonify, send_file
import os

docs_bp = Blueprint('docs', __name__)

@docs_bp.route('/docs-static', methods=['GET'])
def api_docs_static():
    """Serve static API documentation HTML from client/public"""
    # Get path to client/public/api-docs.html
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    docs_path = os.path.join(current_dir, '..', 'client', 'public', 'api-docs.html')
    docs_path = os.path.abspath(docs_path)
    
    if os.path.exists(docs_path):
        return send_file(docs_path, mimetype='text/html')
    else:
        return jsonify({
            "error": "Documentation not found",
            "path": docs_path
        }), 404

@docs_bp.route('/docs.json', methods=['GET'])
def api_docs_json():
    """Get API documentation metadata as JSON"""
    return jsonify({
        "version": "1.0.0",
        "base_url": "/api/v1",
        "total_endpoints": 78,
        "authentication": "JWT Bearer Token / API Token",
        "documentation_url": "/api/docs",
        "legacy_static_docs_url": "/api/docs-static",
        "categories": [
            {"name": "Admin", "count": 15},
            {"name": "Reports", "count": 8},
            {"name": "Downloads", "count": 8},
            {"name": "Authentication", "count": 6},
            {"name": "Alerts", "count": 6},
            {"name": "Members Management", "count": 6},
            {"name": "Payment Methods", "count": 5},
            {"name": "Blocklist", "count": 4},
            {"name": "Whitelist", "count": 4},
            {"name": "Notifications", "count": 3},
            {"name": "API Tokens", "count": 3},
            {"name": "Settings", "count": 3},
            {"name": "Subscription", "count": 3},
            {"name": "Core", "count": 6}
        ]
    })
