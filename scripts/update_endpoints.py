#!/usr/bin/env python3
"""
Update blocklist and whitelist endpoints to remove user_id filters
and add proper role-based authorization
"""
import sys
import os

# Read blocklist.py
blocklist_path = '/home/d4lt0n/Documents/finalProjectCS4/test/Final/server/app/blueprints/blocklist.py'
with open(blocklist_path, 'r') as f:
    content = f.read()

# Replace patterns
content = content.replace(
    "query = BlockedIP.query.filter_by(user_id=user_id, company_id=user.company_id, is_active=True)",
    "query = BlockedIP.query.filter_by(company_id=user.company_id, is_active=True)"
)

content = content.replace(
    "@require_company_role({'admin', 'user'})\ndef add_to_blocklist():",
    "@require_company_role({'admin', 'fully_privileged'})\ndef add_to_blocklist():"
)

content = content.replace(
    "whitelisted = WhitelistedIP.query.filter_by(\n            user_id=user_id,\n            company_id=user.company_id,",
    "whitelisted = WhitelistedIP.query.filter_by(\n            company_id=user.company_id,"
)

content = content.replace(
    "existing = BlockedIP.query.filter_by(\n            user_id=user_id,\n            company_id=user.company_id,",
    "existing = BlockedIP.query.filter_by(\n            company_id=user.company_id,"
)

content = content.replace(
    "success = firewall_service.block_ip(\n            user_id=user_id,\n            company_id=user.company_id,",
    "success = firewall_service.block_ip(\n            company_id=user.company_id,"
)

content = content.replace(
    "@require_company_role({'admin', 'user'})\ndef remove_from_blocklist(",
    "@require_company_role({'admin', 'fully_privileged'})\ndef remove_from_blocklist("
)

content = content.replace(
    "success = firewall_service.unblock_ip(blocked_ip_id, user_id, user.company_id)",
    "success = firewall_service.unblock_ip(blocked_ip_id, user.company_id)"
)

content = content.replace(
    "@require_company_role({'admin', 'user'})\ndef update_blocklist_entry(",
    "@require_company_role({'admin', 'fully_privileged'})\ndef update_blocklist_entry("
)

content = content.replace(
    "blocked_ip = BlockedIP.query.filter_by(\n        id=blocked_ip_id, user_id=user_id, company_id=user.company_id, is_active=True",
    "blocked_ip = BlockedIP.query.filter_by(\n        id=blocked_ip_id, company_id=user.company_id, is_active=True"
)

# Write back
with open(blocklist_path, 'w') as f:
    f.write(content)

print("✓ Updated blocklist.py")

# Update whitelist.py similarly
whitelist_path = '/home/d4lt0n/Documents/finalProjectCS4/test/Final/server/app/blueprints/whitelist.py'
with open(whitelist_path, 'r') as f:
    content = f.read()

content = content.replace(
    "query = WhitelistedIP.query.filter_by(user_id=user_id, company_id=user.company_id, is_active=True)",
    "query = WhitelistedIP.query.filter_by(company_id=user.company_id, is_active=True)"
)

content = content.replace(
    "@require_company_role({'admin', 'user'})\ndef add_to_whitelist():",
    "@require_company_role({'admin', 'fully_privileged'})\ndef add_to_whitelist():"
)

content = content.replace(
    "blocked = BlockedIP.query.filter_by(\n            user_id=user_id,\n            company_id=user.company_id,",
    "blocked = BlockedIP.query.filter_by(\n            company_id=user.company_id,"
)

content = content.replace(
    "existing = WhitelistedIP.query.filter_by(\n            user_id=user_id,\n            company_id=user.company_id,",
    "existing = WhitelistedIP.query.filter_by(\n            company_id=user.company_id,"
)

content = content.replace(
    "success = firewall_service.whitelist_ip(\n            user_id=user_id,\n            company_id=user.company_id,",
    "success = firewall_service.whitelist_ip(\n            company_id=user.company_id,"
)

content = content.replace(
    "@require_company_role({'admin', 'user'})\ndef remove_from_whitelist(",
    "@require_company_role({'admin', 'fully_privileged'})\ndef remove_from_whitelist("
)

content = content.replace(
    "success = firewall_service.unwhitelist_ip(whitelisted_ip_id, user_id, user.company_id)",
    "success = firewall_service.unwhitelist_ip(whitelisted_ip_id, user.company_id)"
)

content = content.replace(
    "@require_company_role({'admin', 'user'})\ndef update_whitelist_entry(",
    "@require_company_role({'admin', 'fully_privileged'})\ndef update_whitelist_entry("
)

content = content.replace(
    "whitelisted_ip = WhitelistedIP.query.filter_by(\n        id=whitelisted_ip_id, user_id=user_id, company_id=user.company_id, is_active=True",
    "whitelisted_ip = WhitelistedIP.query.filter_by(\n        id=whitelisted_ip_id, company_id=user.company_id, is_active=True"
)

with open(whitelist_path, 'w') as f:
    f.write(content)

print("✓ Updated whitelist.py")
print("\nAll endpoint files updated successfully!")
