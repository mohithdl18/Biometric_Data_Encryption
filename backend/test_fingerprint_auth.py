#!/usr/bin/env python3
"""
Test script for fingerprint authentication
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from mongodb_client import get_database
from finger.match.finger_match import R307FingerMatcher

def test_fingerprint_auth():
    print("=== Fingerprint Authentication Test ===")
    
    # Connect to database
    db = get_database()
    if not db.client:
        print("❌ Failed to connect to database")
        return
    
    # Get user information
    username = "MOHITH D L"
    user_data = db.get_user(username)
    
    if not user_data:
        print(f"❌ User {username} not found in database")
        return
        
    print(f"✅ User {username} found")
    print(f"   - Algorithm: {user_data.get('fingerprint_algorithm', 'legacy')}")
    print(f"   - Has template: {bool(user_data.get('fingerprint_template'))}")
    
    # Get template data
    template_data = db.get_fingerprint_template(username)
    if not template_data:
        print("❌ No template data found")
        return
        
    print(f"✅ Template data retrieved: {len(template_data)} bytes")
    
    # Test fingerprint matching
    matcher = R307FingerMatcher()
    print("\n=== Starting Authentication Test ===")
    
    success, confidence, message = matcher.authenticate_user_with_template(username, template_data)
    
    if success:
        print(f"✅ Authentication successful!")
        print(f"   - Confidence: {confidence}")
        print(f"   - Message: {message}")
    else:
        print(f"❌ Authentication failed!")
        print(f"   - Message: {message}")
        print(f"   - Confidence: {confidence}")

if __name__ == "__main__":
    test_fingerprint_auth()
