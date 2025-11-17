#!/usr/bin/env python3
"""
Comprehensive Email Service Diagnostic Tool
Diagnose and fix email delivery issues
"""

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from mail import get_email_service
from email_config import *

def check_mailjet_account_status():
    """Check Mailjet account status and sender verification"""
    print("=== Mailjet Account Status Check ===")
    
    try:
        from mailjet_rest import Client
        
        # Initialize Mailjet client
        mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3')
        
        # Check account information
        print("📊 Checking account information...")
        account_result = mailjet.get_account()
        
        if account_result.status_code == 200:
            account_data = account_result.json()
            print("✅ Account API access working")
            print(f"   Account Status: {account_data.get('Data', [{}])[0].get('Status', 'Unknown')}")
        else:
            print(f"❌ Account API error: {account_result.status_code}")
        
        # Check sender addresses
        print("\n📧 Checking sender addresses...")
        sender_result = mailjet.sender()
        
        if sender_result.status_code == 200:
            senders = sender_result.json().get('Data', [])
            print(f"✅ Found {len(senders)} sender addresses:")
            
            sender_verified = False
            for sender in senders:
                email = sender.get('Email', '')
                status = sender.get('Status', 'Unknown')
                print(f"   📧 {email}: {status}")
                
                if email.lower() == SENDER_EMAIL.lower() and status.lower() == 'active':
                    sender_verified = True
            
            if sender_verified:
                print(f"✅ Sender email {SENDER_EMAIL} is verified and active!")
            else:
                print(f"⚠️  Sender email {SENDER_EMAIL} is not verified!")
                print("   📝 To verify your sender email:")
                print("   1. Go to https://app.mailjet.com/account/sender")
                print("   2. Add your sender email address")
                print("   3. Check email for verification link")
                print("   4. Click the verification link")
        else:
            print(f"❌ Sender API error: {sender_result.status_code}")
            print(f"   Response: {sender_result.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking Mailjet account: {e}")
        return False

def test_email_delivery_detailed():
    """Test email delivery with detailed debugging"""
    print("\n=== Detailed Email Delivery Test ===")
    
    email_service = get_email_service()
    
    if not email_service.mailjet:
        print("❌ Email service not initialized")
        return False
    
    # Ask for test email
    print(f"\n📧 Current sender: {SENDER_EMAIL}")
    test_email = input("Enter recipient email for testing (or press Enter to use sender email): ").strip()
    
    if not test_email:
        test_email = SENDER_EMAIL
    
    print(f"🧪 Testing email delivery to: {test_email}")
    
    # Send test email with detailed tracking
    try:
        from mailjet_rest import Client
        
        mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')
        
        # Prepare test email
        email_data = {
            'Messages': [
                {
                    "From": {
                        "Email": SENDER_EMAIL,
                        "Name": SENDER_NAME
                    },
                    "To": [
                        {
                            "Email": test_email,
                            "Name": "Test User"
                        }
                    ],
                    "Subject": "🔧 Email Service Diagnostic Test",
                    "HTMLPart": """
                    <div style="font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5;">
                        <div style="background: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto;">
                            <h1 style="color: #333; text-align: center;">🔧 Email Service Diagnostic</h1>
                            <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0;">
                                <h3 style="color: #2d5a2d; margin: 0;">✅ Email Delivery Working!</h3>
                                <p style="margin: 10px 0 0 0;">If you're reading this, your biometric authentication system's email service is working correctly.</p>
                            </div>
                            <div style="margin: 20px 0;">
                                <h4>📊 Test Details:</h4>
                                <p><strong>Sender:</strong> {sender_name} &lt;{sender_email}&gt;</p>
                                <p><strong>Recipient:</strong> {test_email}</p>
                                <p><strong>Timestamp:</strong> {timestamp}</p>
                                <p><strong>Service:</strong> Mailjet API v3.1</p>
                            </div>
                            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                                <h4 style="color: #856404; margin: 0 0 10px 0;">📝 Next Steps:</h4>
                                <ol style="margin: 0; color: #856404;">
                                    <li>Check that this email didn't go to spam/junk folder</li>
                                    <li>Verify sender email in Mailjet dashboard</li>
                                    <li>Test registration and login flows in your app</li>
                                </ol>
                            </div>
                        </div>
                    </div>
                    """.format(
                        sender_name=SENDER_NAME,
                        sender_email=SENDER_EMAIL,
                        test_email=test_email,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ),
                    "TextPart": f"""
Email Service Diagnostic Test

✅ EMAIL DELIVERY WORKING!

If you're reading this, your biometric authentication system's email service is working correctly.

Test Details:
- Sender: {SENDER_NAME} <{SENDER_EMAIL}>
- Recipient: {test_email}
- Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Service: Mailjet API v3.1

Next Steps:
1. Check that this email didn't go to spam/junk folder
2. Verify sender email in Mailjet dashboard
3. Test registration and login flows in your app

Biometric Authentication System - Email Service
                    """
                }
            ]
        }
        
        # Send the email
        result = mailjet.send.create(data=email_data)
        
        print(f"\n📤 Email send result:")
        print(f"   Status Code: {result.status_code}")
        
        if result.status_code == 200:
            response_data = result.json()
            message_info = response_data.get('Messages', [{}])[0]
            
            print(f"   Message Status: {message_info.get('Status', 'Unknown')}")
            
            if message_info.get('To'):
                to_info = message_info['To'][0]
                print(f"   Message ID: {to_info.get('MessageID', 'Unknown')}")
                print(f"   Message UUID: {to_info.get('MessageUUID', 'Unknown')}")
                print(f"   Message URL: {to_info.get('MessageHref', 'Unknown')}")
            
            print("\n✅ Email sent successfully!")
            print(f"📬 Check your inbox at {test_email}")
            print("⚠️  If you don't see the email, check:")
            print("   1. Spam/Junk folder")
            print("   2. Promotions tab (Gmail)")
            print("   3. All Mail folder")
            
            return True
        else:
            print(f"❌ Email sending failed!")
            print(f"   Error: {result.text}")
            return False
            
    except Exception as e:
        print(f"❌ Email sending error: {e}")
        import traceback
        traceback.print_exc()
        return False

def diagnose_common_issues():
    """Diagnose common email delivery issues"""
    print("\n=== Common Issue Diagnosis ===")
    
    issues_found = []
    
    # Check sender email format
    if "@" not in SENDER_EMAIL or "." not in SENDER_EMAIL.split("@")[1]:
        issues_found.append("Invalid sender email format")
    
    # Check sender email domain
    sender_domain = SENDER_EMAIL.split("@")[1].lower()
    common_providers = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
    
    if sender_domain not in common_providers:
        issues_found.append("Custom domain may need additional verification")
    
    # Check API credentials
    if len(MAILJET_API_KEY) < 30:
        issues_found.append("API key appears too short")
    
    if len(MAILJET_SECRET_KEY) < 30:
        issues_found.append("Secret key appears too short")
    
    # Check email settings
    if not ENABLE_LOGIN_NOTIFICATIONS:
        issues_found.append("Login notifications are disabled")
    
    if issues_found:
        print("⚠️  Potential issues found:")
        for issue in issues_found:
            print(f"   • {issue}")
    else:
        print("✅ No obvious configuration issues detected")
    
    # Recommendations
    print("\n💡 Recommendations:")
    print("1. Verify sender email in Mailjet dashboard:")
    print("   https://app.mailjet.com/account/sender")
    print("2. Check email delivery reports in Mailjet:")
    print("   https://app.mailjet.com/stats/message")
    print("3. Add SPF/DKIM records if using custom domain")
    print("4. Start with low volume to build sender reputation")

def main():
    """Main diagnostic function"""
    print("🔧 Email Service Diagnostic Tool")
    print("=" * 50)
    
    try:
        # Check configuration
        print(f"📧 Sender Email: {SENDER_EMAIL}")
        print(f"🏷️  Sender Name: {SENDER_NAME}")
        print(f"🔑 API Key: {MAILJET_API_KEY[:10]}...")
        print(f"🔐 Secret Key: {MAILJET_SECRET_KEY[:10]}...")
        
        # Check Mailjet account
        check_mailjet_account_status()
        
        # Test email delivery
        test_email_delivery_detailed()
        
        # Diagnose issues
        diagnose_common_issues()
        
        print("\n" + "=" * 50)
        print("🎯 Email Service Diagnostic Complete")
        
    except KeyboardInterrupt:
        print("\n⛔ Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    main()
