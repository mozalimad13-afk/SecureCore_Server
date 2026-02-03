"""Security Headers Middleware.

Adds secure HTTP headers (including CSP) to all responses.
"""

from flask import g, request
import logging

from config import Config

logger = logging.getLogger(__name__)


def add_security_headers(response):
    """
    Add security headers to response
    
    Args:
        response: Flask response object
    
    Returns:
        Modified response with security headers
    """
    # Apply configured security headers
    for header, value in Config.SECURITY_HEADERS.items():
        response.headers[header] = value

    # Remove information disclosure headers
    response.headers.pop('Server', None)
    response.headers.pop('X-Powered-By', None)

    # Modern security headers
    response.headers['Permissions-Policy'] = Config.PERMISSIONS_POLICY
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

    # HSTS (only meaningful when served over HTTPS)
    if getattr(Config, 'HSTS_ENABLED', False):
        hsts = f"max-age={int(Config.HSTS_MAX_AGE)}"
        if getattr(Config, 'HSTS_INCLUDE_SUBDOMAINS', False):
            hsts += '; includeSubDomains'
        if getattr(Config, 'HSTS_PRELOAD', False):
            hsts += '; preload'
        response.headers['Strict-Transport-Security'] = hsts

    # Content-Security-Policy
    if getattr(Config, 'CSP_ENABLED', False):
        def _uniq(items):
            out = []
            for i in items:
                if i and i not in out:
                    out.append(i)
            return out

        script_src = _uniq(Config.CSP_SCRIPT_SRC + Config.CSP_EXTRA_SCRIPT_SRC)
        style_src = _uniq(Config.CSP_STYLE_SRC + Config.CSP_EXTRA_STYLE_SRC)
        connect_src = _uniq(Config.CSP_CONNECT_SRC + Config.CSP_EXTRA_CONNECT_SRC)
        img_src = _uniq(Config.CSP_IMG_SRC + Config.CSP_EXTRA_IMG_SRC)

        directives = {
            'default-src': _uniq(Config.CSP_DEFAULT_SRC),
            'base-uri': _uniq(Config.CSP_BASE_URI),
            'object-src': _uniq(Config.CSP_OBJECT_SRC),
            'frame-ancestors': _uniq(Config.CSP_FRAME_ANCESTORS),
            'form-action': _uniq(Config.CSP_FORM_ACTION),
            'script-src': script_src,
            'style-src': style_src,
            'img-src': img_src,
            'font-src': _uniq(Config.CSP_FONT_SRC),
            'connect-src': connect_src,
        }

        parts = []
        for k, v in directives.items():
            parts.append(f"{k} {' '.join(v)}")
        if getattr(Config, 'CSP_UPGRADE_INSECURE_REQUESTS', False):
            parts.append('upgrade-insecure-requests')

        csp_value = '; '.join(parts)
        header_name = 'Content-Security-Policy-Report-Only' if getattr(Config, 'CSP_REPORT_ONLY', False) else 'Content-Security-Policy'
        response.headers[header_name] = csp_value
    
    # CORS headers (if applicable)
    if Config.CORS_ENABLED and hasattr(g, 'origin'):
        response.headers['Access-Control-Allow-Origin'] = g.origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    return response
