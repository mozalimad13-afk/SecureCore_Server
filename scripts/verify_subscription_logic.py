import sys
import os
from datetime import datetime

# Add server directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(script_dir)
sys.path.append(server_dir)

from app import create_app
from app.extensions import db
from app.models.company import Company
from app.models.user import User
from app.models.subscription import Subscription
from app.models.token import APIToken
from app.websocket.server import WebSocketInferenceServer

def verify_logic():
    app = create_app()
    with app.app_context():
        print("--- Verifying Subscription Logic ---")
        
        # 1. Setup test data
        test_email = f"test_{int(datetime.now().timestamp())}@example.com"
        company = Company(public_id=Company.generate_public_id(), name="Test Company")
        db.session.add(company)
        db.session.flush()
        
        user = User(email=test_email, name="Test User", company_id=company.id, is_active=True)
        user.set_password("password")
        db.session.add(user)
        
        # Initial subscription (simulating registration fix)
        sub = Subscription(company_id=company.id, plan_name="Free Trial", status="trial", plan_price=0.0)
        db.session.add(sub)
        
        test_token_str = 'test-token-123'
        import hashlib
        test_token_hash = hashlib.sha256(test_token_str.encode()).hexdigest()
        token = APIToken(company_id=company.id, name="Test Token", token_hash=test_token_hash, token_prefix="test-token-123", is_active=True)
        db.session.add(token)
        db.session.commit()
        
        print(f"Created test user: {test_email}")
        print(f"Initial subscription status: {sub.status}")
        
        # 2. Test WebSocket authentication (Mocking socketio)
        ws_server = WebSocketInferenceServer(None, app)
        
        auth_data = {'api_token': 'test-token-123'}
        success, result = ws_server.authenticate_connection(auth_data)
        
        if success and sub.status == 'trial':
            print("✓ SUCCESS: Trial user allowed to connect")
        else:
            print(f"✗ FAILURE: Trial user blocked. Error: {result}")
            return
            
        # 3. Simulate cancellation (User side)
        print("\nCanceling subscription...")
        sub.plan_name = 'Cancelled'
        sub.status = 'cancelled'
        db.session.commit()
        print(f"Subscription status: {sub.status}")
        
        success, result = ws_server.authenticate_connection(auth_data)
        if not success and 'Active subscription required' in str(result):
            print("✓ SUCCESS: Canceled user blocked from WebSocket")
        else:
            print(f"✗ FAILURE: Canceled user allowed. Success: {success}, Result: {result}")
            
        # 4. Simulate resubscribe
        print("\nResubscribing...")
        sub.plan_name = 'Small Companies'
        sub.status = 'active'
        db.session.commit()
        print(f"Subscription status: {sub.status}")
        
        success, result = ws_server.authenticate_connection(auth_data)
        if success:
            print("✓ SUCCESS: Active user allowed to connect")
        else:
            print(f"✗ FAILURE: Active user blocked. Error: {result}")

        # Cleanup
        db.session.delete(token)
        db.session.delete(sub)
        db.session.delete(user)
        db.session.delete(company)
        db.session.commit()
        print("\nVerification completed and cleaned up.")

if __name__ == "__main__":
    verify_logic()
