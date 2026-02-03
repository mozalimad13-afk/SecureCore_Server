"""OpenAPI + Swagger UI documentation.

This blueprint exposes:
- GET /api/openapi.json : OpenAPI 3.0 document
- GET /api/docs         : Swagger UI

We keep the implementation lightweight and code-owned (generated from registered
Flask routes, with minimal auth + request/response shape hints).
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request


openapi_bp = Blueprint('openapi_docs', __name__)


def _merge_dict(dest: dict, src: dict) -> dict:
    """Deep-merge `src` into `dest` (dicts only)."""
    for key, value in (src or {}).items():
        if isinstance(value, dict) and isinstance(dest.get(key), dict):
            _merge_dict(dest[key], value)
        else:
            dest[key] = value
    return dest


def _curated_overrides() -> dict:
    """Hand-authored OpenAPI details for the most important endpoints.

    This keeps the docs accurate and useful without requiring a heavy framework.
    """

    json_ct = {'application/json': {'schema': {'type': 'object'}}}
    empty_json_body = {
        'required': False,
        'content': {
            'application/json': {
                'schema': {'type': 'object', 'additionalProperties': False},
                'examples': {
                    'empty': {'summary': 'No body required', 'value': {}},
                },
            }
        },
    }

    return {
        '/api/v1/auth/login': {
            'post': {
                'summary': 'Login (sets JWT cookies)',
                'description': 'Mobile/web login. Web uses HttpOnly cookies; mobile can still read JSON body. Optional `device_id` is encrypted and stored in `fcm_devices`.',
                'security': [],
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['email', 'password'],
                                'properties': {
                                    'email': {'type': 'string', 'format': 'email'},
                                    'password': {'type': 'string', 'format': 'password'},
                                    'device_id': {'type': 'string', 'description': 'Mobile device identifier (stored encrypted).'},
                                },
                            },
                            'examples': {
                                'minimal': {
                                    'summary': 'Minimal login',
                                    'value': {
                                        'email': 'user@example.com',
                                        'password': 'your-password'
                                    }
                                },
                                'mobile_with_device': {
                                    'summary': 'Mobile login with device_id',
                                    'value': {
                                        'email': 'user@example.com',
                                        'password': 'your-password',
                                        'device_id': 'android-device-123'
                                    }
                                }
                            }
                        }
                    },
                },
                'responses': {
                    '200': {
                        'description': 'Logged in; JWT cookies set',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'csrf_token': {'type': 'string'},
                                        'user': {'type': 'object'},
                                    },
                                }
                            }
                        },
                    },
                    '400': {'description': 'Email/password missing'},
                    '401': {'description': 'Invalid credentials'},
                    '403': {'description': 'Account inactive'},
                },
            }
        },
        '/api/v1/auth/register': {
            'post': {
                'summary': 'Register a new user',
                'security': [],
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['email', 'password', 'name'],
                                'properties': {
                                    'email': {'type': 'string', 'format': 'email'},
                                    'password': {'type': 'string', 'format': 'password'},
                                    'name': {'type': 'string', 'description': 'Full name of the user'},
                                    'company': {'type': 'string', 'description': 'Company name for the tenant'},
                                    'phone': {'type': 'string', 'description': 'Company phone number'},
                                    'country': {'type': 'string', 'description': 'Country code or name'},
                                    'payment_data': {
                                        'type': 'object',
                                        'description': 'Optional payment method fields to store (dev/testing).',
                                        'properties': {
                                            'card_number': {'type': 'string'},
                                            'card_name': {'type': 'string'},
                                            'expiry_month': {'type': 'string', 'example': '12'},
                                            'expiry_year': {'type': 'string', 'example': '28'},
                                            'cvv': {'type': 'string', 'example': '123'},
                                            'billing_address': {'type': 'string'},
                                            'city': {'type': 'string'},
                                            'zip_code': {'type': 'string'},
                                        },
                                    },
                                },
                            },
                            'examples': {
                                'minimal': {
                                    'summary': 'Register without payment',
                                    'value': {
                                        'email': 'newuser@example.com',
                                        'password': 'strong-password',
                                        'name': 'Alice Example',
                                        'company': 'Acme Inc',
                                        'phone': '+1-555-0100',
                                        'country': 'US'
                                    }
                                }
                            }
                        }
                    }
                },
            }
        },
        '/api/v1/locations/countries': {
            'get': {
                'summary': 'List countries',
                'security': [],
                'responses': {
                    '200': {
                        'description': 'Country list',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'countries': {
                                            'type': 'array',
                                            'items': {
                                                'type': 'object',
                                                'properties': {
                                                    'id': {'type': 'integer'},
                                                    'code': {'type': 'string'},
                                                    'name': {'type': 'string'},
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        '/api/v1/auth/me': {
            'get': {'summary': 'Get current user (cookie JWT)'},
            'put': {
                'summary': 'Update current user profile',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'username': {'type': 'string'},
                                    'email': {'type': 'string', 'format': 'email'},
                                    'currentPassword': {'type': 'string', 'format': 'password'},
                                    'newPassword': {'type': 'string', 'format': 'password'},
                                },
                            },
                            'examples': {
                                'update_username': {
                                    'summary': 'Update username',
                                    'value': {'username': 'new_username'}
                                },
                                'change_password': {
                                    'summary': 'Change password',
                                    'value': {
                                        'currentPassword': 'old-pass',
                                        'newPassword': 'new-pass'
                                    }
                                }
                            }
                        }
                    }
                }
            },
        },
        '/api/v1/tokens': {
            'get': {'summary': 'List API tokens'},
        },
        '/api/v1/tokens/generate': {
            'post': {
                'summary': 'Generate API token (revokes existing)',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {'name': {'type': 'string'}},
                            }
                            ,
                            'examples': {
                                'named': {'summary': 'Name the token', 'value': {'name': 'My API Token'}},
                            }
                        }
                    },
                },
                'responses': {
                    '201': {'description': 'Token generated', 'content': json_ct},
                    '403': {'description': 'Subscription suspended'},
                },
            }
        },
        '/api/v1/tokens/usage': {
            'get': {
                'summary': 'Token usage statistics',
                'responses': {
                    '200': {
                        'description': 'Usage summary',
                        'content': {
                            'application/json': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'total_requests_today': {'type': 'integer'},
                                        'active_tokens': {'type': 'integer'},
                                        'tokens': {'type': 'array', 'items': {'type': 'object'}},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        '/api/v1/alerts': {
            'get': {
                'summary': 'List alerts',
                'parameters': [
                    {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}},
                    {'name': 'per_page', 'in': 'query', 'schema': {'type': 'integer'}},
                ],
            }
        },
        '/api/v1/admin/notifications/send': {
            'post': {
                'summary': 'Send admin broadcast notification',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['title', 'message'],
                                'properties': {
                                    'title': {'type': 'string'},
                                    'message': {'type': 'string'},
                                    'severity': {'type': 'string', 'enum': ['info', 'warning', 'critical']},
                                    'target_type': {'type': 'string', 'enum': ['all', 'single', 'selected']},
                                    'user_ids': {'type': 'array', 'items': {'type': 'integer'}},
                                },
                            },
                            'examples': {
                                'broadcast_all': {
                                    'summary': 'Broadcast to all users',
                                    'value': {
                                        'title': 'Maintenance',
                                        'message': 'Planned maintenance tonight 11PM.',
                                        'severity': 'info',
                                        'target_type': 'all'
                                    }
                                },
                                'single_user': {
                                    'summary': 'Send to one user',
                                    'value': {
                                        'title': 'Account notice',
                                        'message': 'Please update your profile.',
                                        'severity': 'warning',
                                        'target_type': 'single',
                                        'user_ids': [2]
                                    }
                                }
                            }
                        }
                    },
                },
            }
        },
        '/api/v1/devices': {
            'post': {
                'summary': 'Register device token (FCM)',
                'description': 'Optional endpoint when the mobile app later obtains an FCM device token. Token is encrypted at rest.',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['device_id'],
                                'properties': {
                                    'device_id': {'type': 'string'},
                                    'device_token': {'type': 'string', 'description': 'FCM token (encrypted at rest).'},
                                    'platform': {'type': 'string', 'example': 'android'},
                                    'app_version': {'type': 'string', 'example': '1.0.0'},
                                    'device_name': {'type': 'string', 'example': 'Pixel 8'},
                                },
                            },
                            'examples': {
                                'device_only': {'summary': 'Register device_id only', 'value': {'device_id': 'android-device-123'}},
                                'with_fcm_token': {
                                    'summary': 'Register with FCM token',
                                    'value': {
                                        'device_id': 'android-device-123',
                                        'device_token': 'fcm_token_here',
                                        'platform': 'android',
                                        'app_version': '1.0.0',
                                        'device_name': 'Pixel 8'
                                    }
                                }
                            }
                        }
                    }
                },
            }
        },

        '/api/v1/settings': {
            'put': {
                'summary': 'Update user settings',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'emailNotifications': {'type': 'boolean'},
                                    'smsNotifications': {'type': 'boolean'},
                                    'webhookNotifications': {'type': 'boolean'},
                                    'webhookUrl': {'type': 'string'},
                                    'dailyDigest': {'type': 'boolean'},
                                    'weeklyReport': {'type': 'boolean'},
                                    'digestTime': {'type': 'string', 'example': '08:00'},
                                    'backupFrequency': {'type': 'string', 'example': 'daily'},
                                },
                            },
                            'examples': {
                                'enable_webhook': {
                                    'summary': 'Enable webhook notifications',
                                    'value': {
                                        'webhookNotifications': True,
                                        'webhookUrl': 'https://example.com/webhook'
                                    }
                                },
                            }
                        }
                    }
                }
            }
        },

        '/api/v1/reports': {
            'post': {
                'summary': 'Generate report',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'start_date': {'type': 'string', 'format': 'date-time'},
                                    'end_date': {'type': 'string', 'format': 'date-time'},
                                    'include_alerts': {'type': 'boolean'},
                                    'include_summary': {'type': 'boolean'},
                                    'include_statistics': {'type': 'boolean'},
                                }
                            },
                            'examples': {
                                'last_7_days': {
                                    'summary': 'Last 7 days',
                                    'value': {
                                        'start_date': '2026-01-14T00:00:00Z',
                                        'end_date': '2026-01-21T00:00:00Z',
                                        'include_alerts': True,
                                        'include_summary': True,
                                        'include_statistics': True
                                    }
                                }
                            }
                        }
                    }
                },
            }
        },

        '/api/v1/reports/preview': {
            'post': {
                'summary': 'Preview report',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'start_date': {'type': 'string', 'format': 'date-time'},
                                    'end_date': {'type': 'string', 'format': 'date-time'},
                                }
                            },
                            'examples': {
                                'minimal': {
                                    'summary': 'Date range',
                                    'value': {
                                        'start_date': '2026-01-14T00:00:00Z',
                                        'end_date': '2026-01-21T00:00:00Z'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },

        '/api/v1/reports/upload': {
            'post': {
                'summary': 'Upload report PDF',
                'requestBody': {
                    'required': True,
                    'content': {
                        'multipart/form-data': {
                            'schema': {
                                'type': 'object',
                                'required': ['file'],
                                'properties': {
                                    'file': {'type': 'string', 'format': 'binary', 'description': 'PDF file'},
                                }
                            }
                        }
                    }
                }
            }
        },

        '/api/v1/payment-methods': {
            'post': {
                'summary': 'Add payment method',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['cardNumber', 'cardName', 'expiryDate', 'cvv'],
                                'properties': {
                                    'cardNumber': {'type': 'string'},
                                    'cardName': {'type': 'string'},
                                    'expiryDate': {'type': 'string', 'example': '12/28'},
                                    'cvv': {'type': 'string'},
                                    'billingAddress': {'type': 'string'},
                                    'billingCity': {'type': 'string'},
                                    'billingState': {'type': 'string'},
                                    'billingZip': {'type': 'string'},
                                }
                            },
                            'examples': {
                                'test_card': {
                                    'summary': 'Example card (do not use real cards)',
                                    'value': {
                                        'cardNumber': '4242424242424242',
                                        'cardName': 'Test User',
                                        'expiryDate': '12/28',
                                        'cvv': '123',
                                        'billingAddress': '123 Main St',
                                        'billingCity': 'Testville',
                                        'billingState': 'CA',
                                        'billingZip': '90001'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },

        '/api/v1/subscription/resubscribe': {
            'post': {
                'summary': 'Resubscribe',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'plan': {'type': 'string', 'example': 'Small Companies'},
                                    'cardNumber': {'type': 'string'},
                                    'cardName': {'type': 'string'},
                                    'expiryDate': {'type': 'string', 'example': '12/28'},
                                    'cvv': {'type': 'string'},
                                }
                            },
                            'examples': {
                                'plan_only': {'summary': 'Resubscribe to plan', 'value': {'plan': 'Small Companies'}},
                            }
                        }
                    }
                }
            }
        },

        '/api/v1/blocklist': {
            'post': {
                'summary': 'Add IP to blocklist',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['ip_address'],
                                'properties': {
                                    'ip_address': {'type': 'string', 'example': '192.168.1.10'},
                                    'reason': {'type': 'string'},
                                }
                            },
                            'examples': {
                                'simple': {
                                    'summary': 'Block an IP',
                                    'value': {'ip_address': '192.168.1.10', 'reason': 'Suspicious activity'}
                                }
                            }
                        }
                    }
                }
            }
        },
        '/api/v1/blocklist/{blocked_ip_id}': {
            'patch': {
                'summary': 'Update blocklist entry',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {'type': 'object', 'properties': {'reason': {'type': 'string'}}},
                            'examples': {'update_reason': {'summary': 'Update reason', 'value': {'reason': 'Updated reason'}}}
                        }
                    }
                }
            }
        },

        '/api/v1/whitelist': {
            'post': {
                'summary': 'Add IP to whitelist',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['ip_address'],
                                'properties': {
                                    'ip_address': {'type': 'string', 'example': '192.168.1.20'},
                                    'reason': {'type': 'string'},
                                }
                            },
                            'examples': {
                                'simple': {
                                    'summary': 'Whitelist an IP',
                                    'value': {'ip_address': '192.168.1.20', 'reason': 'Trusted host'}
                                }
                            }
                        }
                    }
                }
            }
        },
        '/api/v1/whitelist/{whitelist_id}': {
            'patch': {
                'summary': 'Update whitelist entry',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {'type': 'object', 'properties': {'reason': {'type': 'string'}}},
                            'examples': {'update_reason': {'summary': 'Update reason', 'value': {'reason': 'Updated reason'}}}
                        }
                    }
                }
            }
        },
        '/api/v1/auth/logout': {
            'post': {
                'summary': 'Logout (clears JWT cookies)',
                'security': [],
                'requestBody': empty_json_body,
                'responses': {
                    '200': {'description': 'Logged out', 'content': json_ct},
                },
            }
        },

        '/api/v1/auth/refresh': {
            'post': {
                'summary': 'Refresh access token (cookie/JWT refresh flow)',
                'security': [],
                'requestBody': empty_json_body,
                'responses': {
                    '200': {'description': 'Refreshed', 'content': json_ct},
                    '401': {'description': 'Missing/invalid refresh token'},
                },
            }
        },

        '/api/v1/alerts/{alert_id}/acknowledge': {
            'put': {
                'summary': 'Acknowledge an alert',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'note': {'type': 'string'},
                                },
                            },
                            'examples': {
                                'with_note': {'summary': 'Acknowledge with note', 'value': {'note': 'Investigating'}},
                                'empty': {'summary': 'Acknowledge (no body)', 'value': {}},
                            },
                        }
                    },
                },
                'responses': {
                    '200': {'description': 'Acknowledged', 'content': json_ct},
                    '404': {'description': 'Alert not found'},
                },
            }
        },

        '/api/v1/notifications/read-all': {
            'put': {
                'summary': 'Mark all notifications as read',
                'requestBody': empty_json_body,
                'responses': {
                    '200': {'description': 'Updated', 'content': json_ct},
                },
            }
        },

        '/api/v1/notifications/{notification_id}/read': {
            'put': {
                'summary': 'Mark a notification as read',
                'requestBody': empty_json_body,
                'responses': {
                    '200': {'description': 'Updated', 'content': json_ct},
                    '404': {'description': 'Notification not found'},
                },
            }
        },

        '/api/v1/payment-methods/{id}/default': {
            'put': {
                'summary': 'Set payment method as default',
                'requestBody': empty_json_body,
                'responses': {
                    '200': {'description': 'Default updated', 'content': json_ct},
                    '404': {'description': 'Payment method not found'},
                },
            }
        },

        '/api/v1/settings/backup/run': {
            'post': {
                'summary': 'Run backup now',
                'requestBody': empty_json_body,
                'responses': {
                    '200': {'description': 'Backup started/completed', 'content': json_ct},
                },
            }
        },

        '/api/v1/subscription/cancel': {
            'post': {
                'summary': 'Cancel subscription',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'reason': {'type': 'string'},
                                },
                            },
                            'examples': {
                                'with_reason': {'summary': 'Cancel with reason', 'value': {'reason': 'No longer needed'}},
                                'empty': {'summary': 'Cancel (no body)', 'value': {}},
                            },
                        }
                    },
                },
                'responses': {
                    '200': {'description': 'Cancelled', 'content': json_ct},
                    '403': {'description': 'Forbidden'},
                },
            }
        },

        '/api/v1/admin/users/{user_id}/activate': {
            'put': {
                'summary': 'Admin: activate user',
                'requestBody': empty_json_body,
                'responses': {
                    '200': {'description': 'Activated', 'content': json_ct},
                    '404': {'description': 'User not found'},
                },
            }
        },

        '/api/v1/admin/users/{user_id}/suspend': {
            'put': {
                'summary': 'Admin: suspend user',
                'requestBody': {
                    'required': False,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {
                                    'reason': {'type': 'string'},
                                },
                            },
                            'examples': {
                                'with_reason': {'summary': 'Suspend with reason', 'value': {'reason': 'Violation of policy'}},
                                'empty': {'summary': 'Suspend (no body)', 'value': {}},
                            },
                        }
                    },
                },
                'responses': {
                    '200': {'description': 'Suspended', 'content': json_ct},
                    '404': {'description': 'User not found'},
                },
            }
        },
        '/api/v1/members': {
            'get': {'summary': 'List company members'},
            'post': {
                'summary': 'Invite/Create new company member',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['email', 'name'],
                                'properties': {
                                    'email': {'type': 'string', 'format': 'email'},
                                    'name': {'type': 'string'},
                                    'role': {'type': 'string', 'enum': ['admin', 'user', 'limited']},
                                    'password': {'type': 'string'},
                                },
                            }
                        }
                    }
                }
            }
        },
        '/api/v1/members/{member_id}/role': {
            'patch': {
                'summary': 'Update member role within company',
                'requestBody': {
                    'required': True,
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'required': ['role'],
                                'properties': {'role': {'type': 'string', 'enum': ['admin', 'user', 'limited']}}
                            }
                        }
                    }
                }
            }
        },
        '/api/v1/members/{member_id}': {
            'delete': {'summary': 'Delete member from company'}
        }
    }


def _server_url() -> str:
    # Best-effort server URL for docs.
    try:
        return request.host_url.rstrip('/')
    except Exception:
        return 'http://localhost:5000'


@openapi_bp.route('/openapi.json', methods=['GET'])
def openapi_json():
    """Return an OpenAPI 3.0 document.

    Note: This is intentionally a minimal spec. It documents endpoints, auth
    mechanism, and high-level request/response shapes.
    """

    spec = {
        'openapi': '3.0.3',
        'info': {
            'title': 'SecureCore IDS API',
            'version': '1.0.0',
            'description': 'REST API for IDS alerts, notifications, IP management, reports, and tokens.',
        },
        'servers': [{'url': _server_url()}],
        'components': {
            'securitySchemes': {
                'bearerAuth': {
                    'type': 'http',
                    'scheme': 'bearer',
                    'bearerFormat': 'JWT',
                    'description': 'Mobile/agent can pass Authorization: Bearer <token>. Browser uses HttpOnly cookies.',
                },
            }
        },
        'paths': {},
        'tags': [],
    }

    # Populate paths from Flask's url map.
    # Include all non-static endpoints so docs reflect the real app.
    from flask import current_app

    tags_seen: set[str] = set()

    for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.endpoint.startswith('static'):
            continue

        # Skip Werkzeug default rules if present.
        if rule.rule.startswith('/static/'):
            continue

        # Convert Flask rules to OpenAPI-style parameters
        path = rule.rule.replace('<int:', '{').replace('<string:', '{').replace('<', '{').replace('>', '}')
        methods = [m for m in rule.methods if m in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}]
        if not methods:
            continue

        if path not in spec['paths']:
            spec['paths'][path] = {}
        pitem = spec['paths'][path]

        # Derive tag/group from blueprint name (endpoint looks like "blueprint.view_func").
        tag = (rule.endpoint.split('.', 1)[0] if '.' in rule.endpoint else 'app').strip() or 'app'
        if tag not in tags_seen:
            tags_seen.add(tag)
            spec['tags'].append({'name': tag})

        for method in methods:
            # Best-effort auth heuristic. Many endpoints rely on cookie JWT.
            # - Auth endpoints and docs/health are public.
            # - Everything else is treated as requiring auth.
            requires_auth = not (
                path.startswith('/api/v1/auth/')
                or path in {'/health', '/'}
                or path.startswith('/api/docs')
                or path.startswith('/api/openapi')
            )

            op = {
                'summary': f"{method} {path}",
                'operationId': rule.endpoint.replace('.', '_') + '_' + method.lower(),
                'tags': [tag],
                'responses': {
                    '200': {'description': 'Success'},
                    '400': {'description': 'Bad Request'},
                    '401': {'description': 'Unauthorized'},
                    '403': {'description': 'Forbidden'},
                },
            }
            if requires_auth:
                op['security'] = [{'bearerAuth': []}]
            pitem[method.lower()] = op

    # Apply curated overrides last so they win.
    overrides = _curated_overrides()
    for path, item in overrides.items():
        if path not in spec['paths']:
            spec['paths'][path] = {}
        # Item is shaped like {"get": {...}, "post": {...}}.
        for method_name, method_overrides in item.items():
            if method_name not in spec['paths'][path]:
                spec['paths'][path][method_name] = {}
            _merge_dict(spec['paths'][path][method_name], method_overrides)

    # Document Socket.IO events (not part of OpenAPI paths, but included as components/extensions).
    # This makes /api/docs a one-stop overview for both REST and realtime.
    spec.setdefault('x-socketio', {
        'namespaces': {
            '/ws/ui': {
                'auth': 'JWT cookie (browser)',
                'client_events': [],
                'server_events': ['connected', 'error', 'alert_created', 'notification_created'],
                'description': 'Real-time UI updates. Events are broadcast to company_{company_id} and user_{user_id} rooms.',
            },
            '/ws/inference': {
                'auth': 'Bearer API token passed in Socket.IO auth payload',
                'client_events': ['inference', 'ping'],
                'server_events': ['connected', 'error', 'inference_queued', 'inference_result', 'pong'],
                'description': 'High-performance inference channel for IDS agents. Requires valid APIToken.',
            },
        }
    })

    return jsonify(spec)


@openapi_bp.route('/endpoints', methods=['GET'])
def endpoints_page():
        """Human-readable list of all REST endpoints + Socket.IO events."""
        from flask import current_app

        rules = []
        for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: r.rule):
                if rule.endpoint.startswith('static') or rule.rule.startswith('/static/'):
                        continue
                methods = sorted([m for m in rule.methods if m in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}])
                if not methods:
                        continue
                rules.append({
                        'methods': ', '.join(methods),
                        'path': rule.rule,
                        'endpoint': rule.endpoint,
                })

        spec = openapi_json().get_json()
        socketio = spec.get('x-socketio', {})

        rows = "\n".join(
                f"<tr><td><code>{r['methods']}</code></td><td><code>{r['path']}</code></td><td><code>{r['endpoint']}</code></td></tr>"
                for r in rules
        )

        def _ns_block(ns: str, meta: dict) -> str:
                client_events = ', '.join(meta.get('client_events', [])) or '(none)'
                server_events = ', '.join(meta.get('server_events', [])) or '(none)'
                auth = meta.get('auth', '')
                return (
                        f"<h3><code>{ns}</code></h3>"
                        f"<div><b>Auth:</b> {auth}</div>"
                        f"<div><b>Client events:</b> <code>{client_events}</code></div>"
                        f"<div><b>Server events:</b> <code>{server_events}</code></div>"
                )

        namespaces = socketio.get('namespaces', {})
        ns_html = "\n".join(_ns_block(ns, meta) for ns, meta in namespaces.items())

        html = f"""<!doctype html>
<html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
        <title>SecureCore IDS Endpoints</title>
        <style>
            body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; padding: 24px; background: #0b0b0d; color: #eaeaea; }}
            a {{ color: #8ab4f8; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
            th, td {{ border-bottom: 1px solid #242428; padding: 10px 8px; text-align: left; vertical-align: top; }}
            th {{ position: sticky; top: 0; background: #0b0b0d; }}
            code {{ background: #141418; padding: 2px 6px; border-radius: 6px; }}
            input {{ width: 100%; padding: 10px; border-radius: 10px; border: 1px solid #242428; background: #141418; color: #eaeaea; }}
            .muted {{ color: #a0a0a8; }}
        </style>
    </head>
    <body>
        <h1>Endpoints</h1>
        <div class=\"muted\">REST routes: {len(rules)}. Swagger UI: <a href=\"/api/docs\">/api/docs</a>. OpenAPI JSON: <a href=\"/api/openapi.json\">/api/openapi.json</a>.</div>
        <p><input id=\"q\" placeholder=\"Filter by path/method/endpoint (e.g. /api/v1/auth)\" /></p>

        <table id=\"t\">
            <thead>
                <tr><th>Methods</th><th>Path</th><th>Handler</th></tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>

        <h2>Socket.IO</h2>
        {ns_html}

        <script>
            const q = document.getElementById('q');
            const tbody = document.querySelector('#t tbody');
            const allRows = Array.from(tbody.querySelectorAll('tr'));
            q.addEventListener('input', () => {{
                const needle = q.value.toLowerCase().trim();
                for (const tr of allRows) {{
                    const hay = tr.innerText.toLowerCase();
                    tr.style.display = (!needle || hay.includes(needle)) ? '' : 'none';
                }}
            }});
        </script>
    </body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
