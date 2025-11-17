# Email Configuration for Biometric Authentication System
# Update these settings before deploying to production

# Mailjet API Configuration
MAILJET_API_KEY = ""
MAILJET_SECRET_KEY = ""  # Mailjet Secret Key
# To get your secret key:
# 1. Go to https://app.mailjet.com/account/apikeys
# 2. Copy your Secret Key
# 3. Paste it above between the quotes

# Email Settings
SENDER_EMAIL = "atmeninja@gmail.com"  # UPDATE WITH YOUR VERIFIED SENDER EMAIL
SENDER_NAME = "Biometric Authentication System"

# Email Templates Configuration
ENABLE_REGISTRATION_EMAILS = True
ENABLE_LOGIN_NOTIFICATIONS = True
ENABLE_ENROLLMENT_EMAILS = True

# Email Debugging
EMAIL_DEBUG = True

# Fallback Settings
EMAIL_FAIL_SILENTLY = True  # Don't fail operations if email fails

"""
SETUP INSTRUCTIONS:

1. Create a Mailjet account at https://www.mailjet.com/
2. Get your API key and Secret key from your Mailjet dashboard
3. Update MAILJET_SECRET_KEY above with your secret key
4. Verify your sender email address in Mailjet
5. Update SENDER_EMAIL with your verified email address
6. Set EMAIL_DEBUG = False for production use

IMPORTANT SECURITY NOTES:
- Never commit actual secret keys to version control
- Use environment variables in production
- Consider using .env files for local development
- Restrict API key permissions in Mailjet dashboard
"""
