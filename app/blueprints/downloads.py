from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

downloads_bp = Blueprint('downloads', __name__)

PLATFORMS = [
    {
        'name': 'Windows',
        'icon': 'Monitor',
        'version': '2.4.1',
        'size': '45 MB',
        'requirements': 'Windows 10 or later',
        'downloadUrl': 'securecore-agent-windows-2.4.1.exe',
        'features': ['System tray integration', 'Auto-start on boot', 'Background monitoring'],
    },
    {
        'name': 'Linux',
        'icon': 'Terminal',
        'version': '2.4.1',
        'size': '38 MB',
        'requirements': 'Ubuntu 20.04+ / CentOS 8+ / Debian 10+',
        'downloadUrl': 'securecore-agent-linux-2.4.1.tar.gz',
        'features': ['Systemd service', 'CLI interface', 'Docker support'],
    },
    {
        'name': 'macOS',
        'icon': 'Apple',
        'version': '2.4.1',
        'size': '42 MB',
        'requirements': 'macOS 11 Big Sur or later',
        'downloadUrl': 'securecore-agent-macos-2.4.1.dmg',
        'features': ['Menu bar app', 'Native notifications', 'Apple Silicon support'],
    },
]

@downloads_bp.route('/metadata', methods=['GET'])
@jwt_required()
def get_metadata():
    """Get available platforms and agents metadata"""
    return jsonify({'platforms': PLATFORMS}), 200

@downloads_bp.route('/client/<platform>', methods=['GET'])
def download_client(platform):
    """Download IDS client"""
    return jsonify({
        'message': f'Download for {platform} not yet available'
    }), 200
