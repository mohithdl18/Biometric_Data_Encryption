# Email Notification System Setup Guide

## Overview

The biometric authentication system now includes comprehensive email notifications using Mailjet API for:

- **Registration Welcome Emails**: Sent when new users register
- **Login Notifications**: Sent when users successfully authenticate
- **Enrollment Completion**: Sent when biometric enrollment is completed

## Features

### 📧 Email Types

1. **Registration Welcome Email**
   - Professional welcome message with system overview
   - Account details and next steps
   - Security features explanation
   - Enrollment instructions

2. **Login Notification Email**
   - Security alert for successful logins
   - Authentication details (method, confidence, time)
   - Security warnings and account monitoring tips

3. **Enrollment Completion Email**
   - Congratulations on biometric enrollment
   - Security features activation confirmation
   - Login process instructions

### 🎨 Email Design

- **Professional HTML Templates**: Beautiful, responsive email designs
- **Brand Consistent**: Matching color schemes and professional layout
- **Mobile Friendly**: Optimized for all devices
- **Plain Text Fallback**: Text versions for email clients that don't support HTML

## Setup Instructions

### 1. Mailjet Account Setup

1. **Create Mailjet Account**
   ```
   Visit: https://www.mailjet.com/
   Sign up for a free account (up to 6,000 emails/month)
   ```

2. **Get API Credentials**
   - Log into your Mailjet dashboard
   - Go to "Account Settings" → "Master Account" → "API Keys"
   - Copy your API Key and Secret Key

3. **Verify Sender Email**
   - Go to "Account Settings" → "Sender Addresses"
   - Add and verify your sender email address
   - Confirm verification through email

### 2. Configuration

1. **Update Email Configuration**
   ```python
   # Edit: backend/email_config.py
   
   MAILJET_SECRET_KEY = "your-secret-key-here"  # Add your secret key
   SENDER_EMAIL = "your-verified-email@domain.com"  # Your verified sender
   SENDER_NAME = "Your App Name"  # Your application name
   ```

2. **Security Best Practices**
   ```python
   # For production, use environment variables:
   import os
   MAILJET_SECRET_KEY = os.environ.get('MAILJET_SECRET_KEY')
   SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
   ```

### 3. Testing

1. **Run Email Test Script**
   ```bash
   cd backend
   python test_email.py
   ```

2. **Test Registration Flow**
   ```bash
   # Start backend server
   python app.py
   
   # Register a new user with valid email
   # Check your inbox for welcome email
   ```

## Configuration Options

### Email Settings (backend/email_config.py)

```python
# Enable/Disable Email Types
ENABLE_REGISTRATION_EMAILS = True    # Welcome emails
ENABLE_LOGIN_NOTIFICATIONS = True    # Login alerts
ENABLE_ENROLLMENT_EMAILS = True      # Enrollment completion

# Debug Settings
EMAIL_DEBUG = True                   # Console logging
EMAIL_FAIL_SILENTLY = True          # Don't break app if email fails
```

### Customization

1. **Email Templates**
   - Edit templates in `backend/mail.py`
   - Modify HTML content, styling, and text
   - Add your brand colors and logos

2. **Email Content**
   ```python
   # Customize subject lines
   subject = "Welcome to Your Biometric App!"
   
   # Add custom fields to templates
   html_content = f"""
   <p>Custom message for {user_name}</p>
   <p>Account ID: {user_id}</p>
   """
   ```

## API Integration

### Registration Email
```python
# Automatic - triggered during user registration
POST /api/register
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "123-456-7890"
}
```

### Login Notification
```python
# Automatic - triggered during successful authentication
# Face recognition or fingerprint authentication
```

### Manual Email Sending
```python
from mail import get_email_service

email_service = get_email_service()

# Send custom email
result = email_service.send_registration_email(
    user_name="John Doe",
    user_email="john@example.com"
)
```

## Troubleshooting

### Common Issues

1. **"Mailjet not initialized" Error**
   ```bash
   # Install mailjet package
   pip install mailjet-rest
   
   # Check email_config.py has secret key
   ```

2. **"Sender not verified" Error**
   - Verify your sender email in Mailjet dashboard
   - Use the exact verified email address

3. **Emails Not Received**
   - Check spam/junk folder
   - Verify recipient email address
   - Check Mailjet delivery reports

4. **API Rate Limits**
   - Free accounts: 6,000 emails/month
   - Upgrade for higher limits
   - Implement email queuing for high volume

### Debug Mode

Enable detailed logging:
```python
# In email_config.py
EMAIL_DEBUG = True

# Check console output for email status
[INFO] Registration email sent to user@example.com: Success
[WARN] Failed to send login email: Invalid sender
```

## Security Considerations

### Best Practices

1. **API Key Security**
   ```python
   # Use environment variables
   export MAILJET_SECRET_KEY="your-secret-key"
   
   # Don't commit keys to version control
   echo "email_config.py" >> .gitignore
   ```

2. **Email Content Security**
   - Sanitize user input in email templates
   - Validate email addresses before sending
   - Rate limit email sending per user

3. **Privacy Protection**
   - Include unsubscribe links in production
   - Follow GDPR/CAN-SPAM regulations
   - Secure email content transmission

## Production Deployment

### Environment Variables
```bash
# Set production environment variables
export MAILJET_API_KEY="your-api-key"
export MAILJET_SECRET_KEY="your-secret-key"
export SENDER_EMAIL="noreply@yourdomain.com"
export SENDER_NAME="Your Biometric App"
```

### Monitoring
```python
# Add email analytics
# Track delivery rates, open rates, click rates
# Monitor failed deliveries
# Set up alerts for email system issues
```

### Scaling
- Consider email queues for high volume
- Implement retry logic for failed sends
- Use email templates service for easier management
- Set up email webhooks for delivery tracking

## Support

### Resources
- **Mailjet Documentation**: https://dev.mailjet.com/
- **API Rate Limits**: https://dev.mailjet.com/guides/#rate-limiting
- **Template Examples**: Check `backend/mail.py` for HTML templates

### Contact
For issues with the email system integration, check:
1. Mailjet service status
2. API key configuration
3. Sender email verification
4. Network connectivity
5. Email template syntax

---

**🎉 Your biometric authentication system now includes professional email notifications!**

Users will receive beautiful, informative emails at each step of their security journey.
