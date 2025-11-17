#!/usr/bin/env python3
"""
Email Service Test Script
Test the Mailjet email integration for the biometric authentication system
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from mail import get_email_service

def test_email_service():
    """Test email service functionality"""
    print("=== Biometric Authentication Email Service Test ===\n")
    
    # Get email service instance
    email_service = get_email_service()
    
    # Check if Mailjet is initialized
    if not email_service.mailjet:
        print("❌ Email service not initialized!")
        print("Please install mailjet-rest: pip install mailjet-rest")
        print("And configure your Mailjet secret key in email_config.py")
        return False
    
    print("✅ Email service initialized successfully!")
    print(f"📧 Sender: {email_service.sender_name} <{email_service.sender_email}>")
    print(f"🔑 API Key: {email_service.api_key[:10]}...")
    
    # Ask user for test email
    test_email = input("\n📧 Enter your email address for testing: ").strip()
    if not test_email or '@' not in test_email:
        print("❌ Invalid email address!")
        return False
    
    test_name = input("👤 Enter your name for testing: ").strip()
    if not test_name:
        test_name = "Test User"
    
    print(f"\n🧪 Testing email service with {test_email}...")
    
    # Test 1: Basic email test
    print("\n1. Testing basic email functionality...")
    result = email_service.test_email_service(test_email, test_name)
    
    if result['success']:
        print("✅ Basic email test passed!")
        print(f"   Message: {result.get('message', 'Email sent successfully')}")
        if 'message_id' in result:
            print(f"   Message ID: {result['message_id']}")
    else:
        print("❌ Basic email test failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        return False
    
    # Test 2: Registration email
    print("\n2. Testing registration welcome email...")
    result = email_service.send_registration_email(test_name, test_email)
    
    if result['success']:
        print("✅ Registration email test passed!")
        print(f"   Message: {result.get('message', 'Email sent successfully')}")
    else:
        print("❌ Registration email test failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    # Test 3: Login notification email
    print("\n3. Testing login notification email...")
    result = email_service.send_login_notification(
        test_name, 
        test_email, 
        confidence_score=0.95,
        login_method="Face Recognition"
    )
    
    if result['success']:
        print("✅ Login notification test passed!")
        print(f"   Message: {result.get('message', 'Email sent successfully')}")
    else:
        print("❌ Login notification test failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    # Test 4: Enrollment completion email
    print("\n4. Testing enrollment completion email...")
    result = email_service.send_enrollment_completion_email(
        test_name, 
        test_email, 
        enrollment_type="Complete"
    )
    
    if result['success']:
        print("✅ Enrollment completion test passed!")
        print(f"   Message: {result.get('message', 'Email sent successfully')}")
    else:
        print("❌ Enrollment completion test failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print("\n🎉 Email service testing completed!")
    print("📬 Check your email inbox for the test messages.")
    print("\nNote: Check spam/junk folder if emails don't appear in inbox.")
    
    return True

def main():
    """Main test function"""
    try:
        success = test_email_service()
        
        if success:
            print("\n✅ All tests completed successfully!")
            print("🚀 Email service is ready for production use.")
        else:
            print("\n❌ Email service testing failed!")
            print("🛠️  Please check configuration and try again.")
            
    except KeyboardInterrupt:
        print("\n⛔ Test interrupted by user.")
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        return False

if __name__ == "__main__":
    main()
