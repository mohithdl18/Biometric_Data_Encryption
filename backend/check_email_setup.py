#!/usr/bin/env python3
"""
Email System Setup Verification
Check if the email system is properly configured without sending actual emails
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

def check_email_configuration():
    """Check email configuration without sending emails"""
    print("=== Email System Configuration Check ===\n")
    
    try:
        # Check if email configuration file exists
        try:
            from email_config import (
                MAILJET_API_KEY,
                MAILJET_SECRET_KEY,
                SENDER_EMAIL,
                SENDER_NAME,
                ENABLE_REGISTRATION_EMAILS,
                ENABLE_LOGIN_NOTIFICATIONS,
                ENABLE_ENROLLMENT_EMAILS
            )
            print("✅ Email configuration file found and loaded")
        except ImportError as e:
            print(f"❌ Email configuration file not found: {e}")
            return False
        
        # Check API key
        if MAILJET_API_KEY and len(MAILJET_API_KEY) > 20:
            print(f"✅ Mailjet API Key configured: {MAILJET_API_KEY[:10]}...")
        else:
            print("❌ Mailjet API Key not configured or invalid")
            return False
        
        # Check secret key
        if MAILJET_SECRET_KEY and len(MAILJET_SECRET_KEY) > 20:
            print(f"✅ Mailjet Secret Key configured: {MAILJET_SECRET_KEY[:10]}...")
        else:
            print("⚠️  Mailjet Secret Key not configured")
            print("   To get your secret key:")
            print("   1. Go to https://app.mailjet.com/account/apikeys")
            print("   2. Copy your Secret Key")
            print("   3. Update MAILJET_SECRET_KEY in email_config.py")
            return False
        
        # Check sender email
        if SENDER_EMAIL and "@" in SENDER_EMAIL:
            print(f"✅ Sender email configured: {SENDER_EMAIL}")
        else:
            print("❌ Sender email not configured or invalid")
            return False
        
        # Check sender name
        if SENDER_NAME:
            print(f"✅ Sender name configured: {SENDER_NAME}")
        else:
            print("❌ Sender name not configured")
        
        # Check email types enabled
        print(f"\n📧 Email Types Status:")
        print(f"   Registration emails: {'✅ Enabled' if ENABLE_REGISTRATION_EMAILS else '❌ Disabled'}")
        print(f"   Login notifications: {'✅ Enabled' if ENABLE_LOGIN_NOTIFICATIONS else '❌ Disabled'}")
        print(f"   Enrollment emails: {'✅ Enabled' if ENABLE_ENROLLMENT_EMAILS else '❌ Disabled'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False

def check_mailjet_package():
    """Check if mailjet-rest package is installed"""
    print("\n=== Package Dependencies Check ===")
    
    try:
        import mailjet_rest
        print("✅ mailjet-rest package is installed")
        print(f"   Version: {getattr(mailjet_rest, '__version__', 'Unknown')}")
        return True
    except ImportError:
        print("❌ mailjet-rest package not installed")
        print("   Install with: pip install mailjet-rest")
        return False

def check_email_integration():
    """Check if email system is integrated with the main app"""
    print("\n=== Integration Check ===")
    
    try:
        # Check if mail.py exists
        if os.path.exists("mail.py"):
            print("✅ mail.py email service module found")
        else:
            print("❌ mail.py email service module not found")
            return False
        
        # Check if main app imports email service
        if os.path.exists("app.py"):
            with open("app.py", "r") as f:
                app_content = f.read()
                if "from mail import get_email_service" in app_content:
                    print("✅ Email service integrated with main app")
                else:
                    print("❌ Email service not integrated with main app")
                    return False
        else:
            print("❌ Main app.py not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Integration check failed: {e}")
        return False

def show_next_steps():
    """Show next steps for completing email setup"""
    print("\n=== Next Steps ===")
    print("1. 🔑 Get Mailjet Secret Key:")
    print("   - Visit: https://app.mailjet.com/account/apikeys")
    print("   - Copy your Secret Key")
    print("   - Update email_config.py with your secret key")
    print()
    print("2. 📧 Verify Sender Email:")
    print("   - Visit: https://app.mailjet.com/account/sender")
    print("   - Add and verify your sender email address")
    print("   - Update SENDER_EMAIL in email_config.py")
    print()
    print("3. 🧪 Test Email System:")
    print("   - Run: python test_email.py")
    print("   - Enter your email address for testing")
    print()
    print("4. 🚀 Start Your Application:")
    print("   - Run: python app.py")
    print("   - Register a new user with valid email")
    print("   - Check your inbox for welcome email")

def main():
    """Main verification function"""
    print("🔍 Verifying Email System Setup...\n")
    
    try:
        # Check configuration
        config_ok = check_email_configuration()
        
        # Check package dependencies
        package_ok = check_mailjet_package()
        
        # Check integration
        integration_ok = check_email_integration()
        
        # Show results
        print("\n" + "="*50)
        if config_ok and package_ok and integration_ok:
            print("🎉 Email system is fully configured and ready!")
            print("✅ All checks passed - you can now test email functionality")
        else:
            print("⚠️  Email system needs additional setup")
            show_next_steps()
        
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n⛔ Check interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()
