#!/usr/bin/env python3
"""
Test API endpoints with the new company-centric architecture
"""
import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_login():
    """Test login endpoint"""
    print("Testing login...")
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "moz.alimad50@gmail.com",
        "password": "123"  # Using the test password
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ Login successful")
        print(f"    User: {data.get('user', {}).get('name')}")
        print(f"    Role: {data.get('user', {}).get('role')}")
        return data.get('access_token')
    else:
        print(f"  ✗ Login failed: {response.status_code}")
        print(f"    {response.text}")
        return None

def test_company_settings(token):
    """Test company settings endpoints"""
    print("\nTesting company settings (admin only)...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get company settings
    response = requests.get(f"{BASE_URL}/settings/company", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ GET /settings/company successful")
        settings = data.get('settings', {})
        print(f"    Email notifications: {settings.get('emailNotifications')}")
        print(f"    Backup frequency: {settings.get('backupFrequency')}")
    elif response.status_code == 403:
        print(f"  ℹ GET /settings/company: Access denied (not admin)")
    else:
        print(f"  ✗ GET /settings/company failed: {response.status_code}")
        print(f"    {response.text}")

def test_user_profile(token):
    """Test user profile endpoints"""
    print("\nTesting user profile (all users)...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get user profile
    response = requests.get(f"{BASE_URL}/settings/profile", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✓ GET /settings/profile successful")
        profile = data.get('profile', {})
        print(f"    Name: {profile.get('name')}")
        print(f"    Email: {profile.get('email')}")
        print(f"    Timezone: {profile.get('timezone')}")
    else:
        print(f"  ✗ GET /settings/profile failed: {response.status_code}")
        print(f"    {response.text}")

def test_tokens(token):
    """Test API tokens endpoints"""
    print("\nTesting API tokens (admin only)...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get tokens
    response = requests.get(f"{BASE_URL}/tokens", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        tokens = data.get('tokens', [])
        print(f"  ✓ GET /tokens successful")
        print(f"    Found {len(tokens)} tokens")
    elif response.status_code == 403:
        print(f"  ℹ GET /tokens: Access denied (not admin)")
    else:
        print(f"  ✗ GET /tokens failed: {response.status_code}")
        print(f"    {response.text}")

def test_payment_methods(token):
    """Test payment methods endpoints"""
    print("\nTesting payment methods (admin only)...")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get payment methods
    response = requests.get(f"{BASE_URL}/payment-methods", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        methods = data.get('payment_methods', [])
        print(f"  ✓ GET /payment-methods successful")
        print(f"    Found {len(methods)} payment methods")
    elif response.status_code == 403:
        print(f"  ℹ GET /payment-methods: Access denied (not admin)")
    else:
        print(f"  ✗ GET /payment-methods failed: {response.status_code}")
        print(f"    {response.text}")

def main():
    print("=" * 60)
    print("API Endpoint Tests - Company-Centric Architecture")
    print("=" * 60)
    print()
    
    # Login first
    token = test_login()
    
    if not token:
        print("\n✗ Cannot proceed without authentication")
        return
    
    # Test endpoints
    test_company_settings(token)
    test_user_profile(token)
    test_tokens(token)
    test_payment_methods(token)
    
    print("\n" + "=" * 60)
    print("API tests completed!")
    print("=" * 60)

if __name__ == '__main__':
    main()
