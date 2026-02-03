#!/usr/bin/env python3
"""
Final cleanup: Remove tenant_id from WebSocketSession creation
"""

websocket_path = '/home/d4lt0n/Documents/finalProjectCS4/test/Final/server/app/websocket/server.py'
with open(websocket_path, 'r') as f:
    content = f.read()

# Remove tenant_id from session creation (model doesn't have this field)
content = content.replace(
    "session = WebSocketSession(\n                tenant_id=user_data.get('company_id'),\n                user_id=user_data['user_id'],",
    "session = WebSocketSession(\n                user_id=user_data['user_id'],"
)

with open(websocket_path, 'w') as f:
    f.write(content)

print("✓ Removed tenant_id from WebSocketSession creation")
print("✓ WebSocket now fully uses company_id (via user relationship)")
