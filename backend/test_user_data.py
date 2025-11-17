#!/usr/bin/env python3
"""
Test script to check MongoDB user data retrieval
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from mongodb_client import get_database

def test_user_retrieval():
    """Test user data retrieval from MongoDB"""
    print("=== MongoDB User Data Test ===\n")
    
    # Connect to database
    db = get_database()
    
    if not db.client:
        print("❌ Cannot connect to database")
        return False
    
    print("✅ Connected to MongoDB successfully!")
    
    # Get all users from the database
    try:
        users_collection = db.db.users
        all_users = list(users_collection.find({}))
        
        print(f"\n📊 Found {len(all_users)} users in database:")
        
        for user in all_users:
            print(f"\n👤 User: {user.get('name', 'Unknown')}")
            print(f"   📧 Email: {user.get('email', 'No email')}")
            print(f"   📱 Phone: {user.get('phone', 'No phone')}")
            print(f"   📅 Created: {user.get('created_at', 'Unknown')}")
            print(f"   🖼️  Face Image: {'✅ Yes' if user.get('face_image_id') else '❌ No'}")
            print(f"   👆 Fingerprint: {'✅ Yes' if user.get('fingerprint_template') else '❌ No'}")
            print(f"   ✅ Complete: {'Yes' if user.get('registration_complete') else 'No'}")
        
        # Test specific user retrieval
        if all_users:
            test_user = all_users[0]
            username = test_user.get('name')
            
            print(f"\n🔍 Testing get_user_info() for: {username}")
            
            # Test using get_user_info method
            user_data = db.get_user_info(username)
            
            if user_data:
                print("✅ get_user_info() working correctly!")
                print(f"   Retrieved data: {user_data}")
                
                if user_data.get('email'):
                    print(f"✅ Email found: {user_data['email']}")
                else:
                    print("❌ No email field in user data")
            else:
                print("❌ get_user_info() returned None")
        
        return True
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    try:
        success = test_user_retrieval()
        
        if success:
            print("\n✅ Database user retrieval test completed!")
        else:
            print("\n❌ Database test failed!")
            
    except KeyboardInterrupt:
        print("\n⛔ Test interrupted by user.")
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")

if __name__ == "__main__":
    main()
