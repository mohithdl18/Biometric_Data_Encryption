#!/usr/bin/env python3
"""
Email Service Module for Biometric Authentication System
Handles email notifications using Mailjet API for registration and login events
"""

import os
import sys
from datetime import datetime
import json

# Import email configuration
try:
    from email_config import (
        MAILJET_API_KEY,
        MAILJET_SECRET_KEY,
        SENDER_EMAIL,
        SENDER_NAME,
        ENABLE_REGISTRATION_EMAILS,
        ENABLE_LOGIN_NOTIFICATIONS,
        ENABLE_ENROLLMENT_EMAILS,
        EMAIL_DEBUG,
        EMAIL_FAIL_SILENTLY
    )
except ImportError:
    # Fallback configuration
    MAILJET_API_KEY = "9ad1db68f970f126768021810ba00691"
    MAILJET_SECRET_KEY = ""
    SENDER_EMAIL = "noreply@biometric-auth.com"
    SENDER_NAME = "Biometric Authentication System"
    ENABLE_REGISTRATION_EMAILS = True
    ENABLE_LOGIN_NOTIFICATIONS = True
    ENABLE_ENROLLMENT_EMAILS = True
    EMAIL_DEBUG = True
    EMAIL_FAIL_SILENTLY = True
    print("[WARN] Email configuration not found. Using default settings.")

class EmailService:
    def __init__(self):
        """Initialize Mailjet email service"""
        self.api_key = MAILJET_API_KEY
        self.secret_key = MAILJET_SECRET_KEY
        self.sender_email = SENDER_EMAIL
        self.sender_name = SENDER_NAME
        self.mailjet = None
        
        # Initialize Mailjet client
        self._init_mailjet()
    
    def _init_mailjet(self):
        """Initialize Mailjet client"""
        try:
            from mailjet_rest import Client
            
            # Initialize Mailjet client
            self.mailjet = Client(auth=(self.api_key, self.secret_key), version='v3.1')
            print("[INFO] Mailjet email service initialized successfully")
            
        except ImportError:
            print("[WARNING] Mailjet package not installed. Email functionality disabled.")
            print("[INFO] Install with: pip install mailjet-rest")
            self.mailjet = None
        except Exception as e:
            print(f"[ERROR] Failed to initialize Mailjet: {e}")
            self.mailjet = None
    
    def send_email(self, to_email, to_name, subject, html_content, text_content=None):
        """
        Send email using Mailjet API
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text email content (optional)
        
        Returns:
            dict: Email sending result
        """
        if not self.mailjet:
            return {
                "success": False,
                "error": "Mailjet not initialized. Email service unavailable."
            }
        
        try:
            # Prepare email data (following Mailjet v3.1 format)
            email_data = {
                'Messages': [
                    {
                        "From": {
                            "Email": self.sender_email,
                            "Name": self.sender_name
                        },
                        "To": [
                            {
                                "Email": to_email,
                                "Name": to_name
                            }
                        ],
                        "Subject": subject,
                        "HTMLPart": html_content
                    }
                ]
            }
            
            # Add text content if provided
            if text_content:
                email_data['Messages'][0]["TextPart"] = text_content
            
            # Send email
            result = self.mailjet.send.create(data=email_data)
            
            print(f"[DEBUG] Mailjet Response Status: {result.status_code}")
            print(f"[DEBUG] Mailjet Response: {result.json()}")
            
            if result.status_code == 200:
                response_data = result.json()
                messages = response_data.get('Messages', [])
                if messages and len(messages) > 0:
                    message_info = messages[0]
                    status = message_info.get('Status', 'unknown')
                    
                    if status == 'success':
                        print(f"[INFO] Email sent successfully to {to_email}")
                        return {
                            "success": True,
                            "message": f"Email sent to {to_email}",
                            "status": status,
                            "message_id": message_info.get('To', [{}])[0].get('MessageID') if message_info.get('To') else None
                        }
                    else:
                        error_info = message_info.get('Errors', [])
                        error_msg = error_info[0].get('ErrorMessage', 'Unknown error') if error_info else 'Email rejected'
                        print(f"[ERROR] Email rejected: {error_msg}")
                        return {
                            "success": False,
                            "error": f"Email rejected: {error_msg}",
                            "status": status,
                            "details": error_info
                        }
                else:
                    print(f"[ERROR] No message data in response")
                    return {
                        "success": False,
                        "error": "No message data in response",
                        "details": response_data
                    }
            else:
                print(f"[ERROR] Failed to send email: {result.status_code} - {result.text}")
                return {
                    "success": False,
                    "error": f"Email sending failed: {result.status_code}",
                    "details": result.text
                }
                
        except Exception as e:
            print(f"[ERROR] Email sending exception: {e}")
            return {
                "success": False,
                "error": f"Email sending failed: {str(e)}"
            }
    
    def send_registration_email(self, user_name, user_email, registration_time=None):
        """
        Send welcome email after successful registration
        
        Args:
            user_name: Name of the registered user
            user_email: Email address of the user
            registration_time: Time of registration (optional)
        
        Returns:
            dict: Email sending result
        """
        if not ENABLE_REGISTRATION_EMAILS:
            return {"success": True, "message": "Registration emails disabled"}
        
        if not registration_time:
            registration_time = datetime.now()
        
        formatted_time = registration_time.strftime("%B %d, %Y at %I:%M %p")
        
        subject = "🎉 Welcome to Biometric Authentication System!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .feature {{ background: white; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Welcome to Biometric Authentication!</h1>
                    <p>Your secure account has been created successfully</p>
                </div>
                
                <div class="content">
                    <h2>Hello {user_name}! 👋</h2>
                    
                    <p>Congratulations! Your biometric authentication account has been successfully created on <strong>{formatted_time}</strong>.</p>
                    
                    <div class="feature">
                        <h3>🎯 What's Next?</h3>
                        <p>Complete your biometric enrollment to unlock full security features:</p>
                        <ul>
                            <li><strong>📷 Face Recognition:</strong> Enroll your face for automatic identification</li>
                            <li><strong>👆 Fingerprint:</strong> Register your fingerprint with our R307 sensor</li>
                            <li><strong>🔒 Dual Authentication:</strong> Enjoy maximum security with combined biometrics</li>
                        </ul>
                    </div>
                    
                    <div class="feature">
                        <h3>🛡️ Security Features</h3>
                        <ul>
                            <li>Advanced face recognition with 6000+ feature points</li>
                            <li>Professional R307 fingerprint sensor integration</li>
                            <li>Cloud-secure MongoDB Atlas database</li>
                            <li>Real-time biometric processing</li>
                        </ul>
                    </div>
                    
                    <div class="feature">
                        <h3>📊 Your Account Details</h3>
                        <p><strong>Name:</strong> {user_name}</p>
                        <p><strong>Email:</strong> {user_email}</p>
                        <p><strong>Registration Date:</strong> {formatted_time}</p>
                        <p><strong>Status:</strong> Active (Enrollment Pending)</p>
                    </div>
                    
                    <p>Thank you for choosing our advanced biometric authentication system. Your security is our priority!</p>
                </div>
                
                <div class="footer">
                    <p>This email was sent from Biometric Authentication System</p>
                    <p>© 2025 Advanced Biometric Security. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Biometric Authentication System!
        
        Hello {user_name}!
        
        Your biometric authentication account has been successfully created on {formatted_time}.
        
        What's Next:
        - Complete face recognition enrollment
        - Register your fingerprint with R307 sensor
        - Enjoy dual biometric authentication
        
        Account Details:
        Name: {user_name}
        Email: {user_email}
        Registration: {formatted_time}
        Status: Active (Enrollment Pending)
        
        Thank you for choosing our advanced biometric authentication system!
        
        © 2025 Advanced Biometric Security
        """
        
        return self.send_email(user_email, user_name, subject, html_content, text_content)
    
    def send_login_notification(self, user_name, user_email, login_time=None, confidence_score=None, login_method="Dual Biometric"):
        """
        Send login notification email
        
        Args:
            user_name: Name of the user who logged in
            user_email: Email address of the user
            login_time: Time of login (optional)
            confidence_score: Authentication confidence score (optional)
            login_method: Method used for login (optional)
        
        Returns:
            dict: Email sending result
        """
        if not ENABLE_LOGIN_NOTIFICATIONS:
            return {"success": True, "message": "Login notifications disabled"}
        
        if not login_time:
            login_time = datetime.now()
        
        formatted_time = login_time.strftime("%B %d, %Y at %I:%M %p")
        confidence_text = f" (Confidence: {confidence_score:.1%})" if confidence_score else ""
        
        subject = f"🔐 Login Alert - {user_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .alert-box {{ background: #e8f5e8; border: 1px solid #4caf50; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .info-box {{ background: white; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 4px solid #4facfe; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .success {{ color: #4caf50; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Login Notification</h1>
                    <p>Secure access to your biometric account</p>
                </div>
                
                <div class="content">
                    <div class="alert-box">
                        <h2 class="success">✅ Successful Login Detected</h2>
                        <p>Hello <strong>{user_name}</strong>! We detected a successful login to your biometric authentication account.</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>📊 Login Details</h3>
                        <p><strong>User:</strong> {user_name}</p>
                        <p><strong>Email:</strong> {user_email}</p>
                        <p><strong>Login Time:</strong> {formatted_time}</p>
                        <p><strong>Authentication Method:</strong> {login_method}{confidence_text}</p>
                        <p><strong>Status:</strong> <span class="success">Authentication Successful</span></p>
                    </div>
                    
                    <div class="info-box">
                        <h3>🛡️ Security Information</h3>
                        <p>Your account was accessed using our advanced biometric authentication system:</p>
                        <ul>
                            <li>Face recognition with advanced feature matching</li>
                            <li>R307 fingerprint sensor verification</li>
                            <li>Real-time biometric processing</li>
                            <li>Secure cloud database authentication</li>
                        </ul>
                    </div>
                    
                    <div class="info-box">
                        <h3>⚠️ Security Notice</h3>
                        <p>If this login was not initiated by you, please contact system administrator immediately. Our biometric system provides high-security authentication, but we recommend monitoring your account activity.</p>
                    </div>
                    
                    <p>Thank you for using our secure biometric authentication system!</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated security notification from Biometric Authentication System</p>
                    <p>© 2025 Advanced Biometric Security. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Biometric Authentication - Login Notification
        
        Hello {user_name}!
        
        We detected a successful login to your biometric authentication account.
        
        Login Details:
        User: {user_name}
        Email: {user_email}
        Time: {formatted_time}
        Method: {login_method}{confidence_text}
        Status: Authentication Successful
        
        Security Features Used:
        - Advanced face recognition
        - R307 fingerprint verification
        - Real-time biometric processing
        - Secure cloud authentication
        
        If this login was not initiated by you, please contact system administrator.
        
        © 2025 Advanced Biometric Security
        """
        
        return self.send_email(user_email, user_name, subject, html_content, text_content)
    
    def send_enrollment_completion_email(self, user_name, user_email, enrollment_type="Complete"):
        """
        Send email when biometric enrollment is completed
        
        Args:
            user_name: Name of the user
            user_email: Email address of the user
            enrollment_type: Type of enrollment completed (Face, Fingerprint, Complete)
        
        Returns:
            dict: Email sending result
        """
        if not ENABLE_ENROLLMENT_EMAILS:
            return {"success": True, "message": "Enrollment emails disabled"}
        
        formatted_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        subject = f"🎉 Biometric Enrollment {enrollment_type} - {user_name}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success-box {{ background: #e8f5e8; border: 1px solid #4caf50; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; }}
                .info-box {{ background: white; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 4px solid #11998e; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                .success {{ color: #4caf50; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Enrollment Complete!</h1>
                    <p>Your biometric security is now active</p>
                </div>
                
                <div class="content">
                    <div class="success-box">
                        <h2 class="success">✅ {enrollment_type} Enrollment Successful!</h2>
                        <p>Congratulations <strong>{user_name}</strong>! Your biometric enrollment has been completed successfully.</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>📊 Enrollment Details</h3>
                        <p><strong>User:</strong> {user_name}</p>
                        <p><strong>Email:</strong> {user_email}</p>
                        <p><strong>Completion Time:</strong> {formatted_time}</p>
                        <p><strong>Enrollment Type:</strong> {enrollment_type}</p>
                        <p><strong>Security Level:</strong> <span class="success">High Security Active</span></p>
                    </div>
                    
                    <div class="info-box">
                        <h3>🔐 Your Security Features</h3>
                        <ul>
                            <li><strong>Advanced Face Recognition:</strong> 6000+ feature point matching</li>
                            <li><strong>Fingerprint Authentication:</strong> R307 sensor with template matching</li>
                            <li><strong>Dual Biometric Verification:</strong> Maximum security protection</li>
                            <li><strong>Real-time Processing:</strong> Instant authentication</li>
                            <li><strong>Cloud Security:</strong> Encrypted MongoDB Atlas storage</li>
                        </ul>
                    </div>
                    
                    <div class="info-box">
                        <h3>🚀 Ready to Login</h3>
                        <p>Your account is now ready for secure biometric login:</p>
                        <ol>
                            <li>Click "Login" on the application</li>
                            <li>Look at the camera for face recognition</li>
                            <li>Confirm your identity</li>
                            <li>Place finger on R307 sensor</li>
                            <li>Access your secure dashboard</li>
                        </ol>
                    </div>
                    
                    <p>Welcome to the future of secure authentication!</p>
                </div>
                
                <div class="footer">
                    <p>Biometric Authentication System - Your Security, Our Priority</p>
                    <p>© 2025 Advanced Biometric Security. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Biometric Enrollment Complete!
        
        Congratulations {user_name}!
        
        Your {enrollment_type} biometric enrollment has been completed successfully on {formatted_time}.
        
        Security Features Active:
        - Advanced Face Recognition (6000+ features)
        - Fingerprint Authentication (R307 sensor)
        - Dual Biometric Verification
        - Real-time Processing
        - Cloud Security (MongoDB Atlas)
        
        Your account is now ready for secure biometric login!
        
        Login Process:
        1. Click "Login" on the application
        2. Look at camera for face recognition
        3. Confirm your identity
        4. Place finger on R307 sensor
        5. Access your secure dashboard
        
        Welcome to the future of secure authentication!
        
        © 2025 Advanced Biometric Security
        """
        
        return self.send_email(user_email, user_name, subject, html_content, text_content)
    
    def test_email_service(self, test_email="test@example.com", test_name="Test User"):
        """
        Test email service functionality
        
        Args:
            test_email: Email address for testing
            test_name: Name for testing
        
        Returns:
            dict: Test result
        """
        print(f"[INFO] Testing email service with {test_email}")
        
        if not self.mailjet:
            return {
                "success": False,
                "error": "Mailjet not initialized. Please install mailjet-rest package."
            }
        
        subject = "🧪 Biometric Authentication System - Email Test"
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧪 Email Service Test</h1>
                    <p>This is a test email from the Biometric Authentication System</p>
                    <p>If you receive this, the email service is working correctly!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = "Email Service Test - Biometric Authentication System\n\nThis is a test email. If you receive this, the email service is working correctly!"
        
        return self.send_email(test_email, test_name, subject, html_content, text_content)

# Global email service instance
email_service = EmailService()

def get_email_service():
    """Get global email service instance"""
    return email_service

def main():
    """Test email service functionality"""
    print("=== Email Service Test ===")
    
    # Initialize email service
    service = get_email_service()
    
    if not service.mailjet:
        print("❌ Email service not available. Install mailjet-rest package.")
        return
    
    # Test email sending
    print("\n1. Testing email service...")
    # result = service.test_email_service("your-test-email@example.com", "Test User")
    
    print("\n2. Testing registration email...")
    # result = service.send_registration_email("John Doe", "john@example.com")
    
    print("\n3. Testing login notification...")
    # result = service.send_login_notification("John Doe", "john@example.com", confidence_score=0.95)
    
    print("\n✅ Email service test completed!")
    print("Note: Update MAILJET_SECRET_KEY and sender email before using in production.")

if __name__ == "__main__":
    main()
