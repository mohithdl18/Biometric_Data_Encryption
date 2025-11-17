#!/usr/bin/env python3
"""
Dashboard Module for Biometric Authentication System
Provides user profile information and photo retrieval endpoints
"""

from flask import Blueprint, request, jsonify, send_file
from mongodb_client import get_database
import io
from datetime import datetime
from bson import ObjectId

# Create dashboard blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

def get_dashboard_database():
    """Get database instance for dashboard operations"""
    return get_database()

@dashboard_bp.route('/user/<username>', methods=['GET'])
def get_user_info(username):
    """
    Get complete user information for dashboard display
    Returns user profile data with biometric status
    """
    try:
        db = get_dashboard_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        # Get user from database
        user = db.get_user(username)
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User "{username}" not found'
            }), 404
        
        # Prepare user information for dashboard
        user_info = {
            '_id': str(user.get('_id', '')),
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'created_at': user.get('created_at', '').isoformat() if user.get('created_at') else None,
            'registration_complete': user.get('registration_complete', False),
            
            # Biometric data status
            'has_face_image': bool(user.get('face_image_id')),
            'has_fingerprint': bool(user.get('fingerprint_template')),
            'has_photo': bool(user.get('face_image_id')),  # For photo display
            
            # Last updated timestamps
            'face_updated_at': user.get('face_updated_at', '').isoformat() if user.get('face_updated_at') else None,
            'fingerprint_updated_at': user.get('fingerprint_updated_at', '').isoformat() if user.get('fingerprint_updated_at') else None,
            
            # Additional metadata
            'account_status': 'Active',
            'security_level': 'High' if user.get('registration_complete', False) else 'Medium',
            'enrollment_percentage': calculate_enrollment_percentage(user)
        }
        
        return jsonify({
            'success': True,
            'user': user_info,
            'message': f'User information retrieved for {username}'
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting user info for {username}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve user information: {str(e)}'
        }), 500

@dashboard_bp.route('/photo/<username>', methods=['GET'])
def get_user_photo(username):
    """
    Get user's face image for dashboard display
    Returns the image file directly
    """
    try:
        db = get_dashboard_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        # Get face image data
        image_data = db.get_face_image(username)
        
        if not image_data:
            return jsonify({
                'success': False,
                'error': f'No photo found for user "{username}"'
            }), 404
        
        # Create BytesIO object for sending image
        image_buffer = io.BytesIO(image_data)
        image_buffer.seek(0)
        
        return send_file(
            image_buffer,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'{username}_photo.jpg'
        )
        
    except Exception as e:
        print(f"❌ Error getting photo for {username}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve photo: {str(e)}'
        }), 500

@dashboard_bp.route('/stats/<username>', methods=['GET'])
def get_user_stats(username):
    """
    Get user statistics and activity information
    """
    try:
        db = get_dashboard_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        user = db.get_user(username)
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User "{username}" not found'
            }), 404
        
        # Calculate user statistics
        stats = {
            'account_age_days': calculate_account_age(user.get('created_at')),
            'biometric_completeness': calculate_enrollment_percentage(user),
            'security_score': calculate_security_score(user),
            'last_activity': get_last_activity(user),
            'data_quality': assess_data_quality(user)
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'message': f'Statistics retrieved for {username}'
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting stats for {username}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve statistics: {str(e)}'
        }), 500

@dashboard_bp.route('/activity/<username>', methods=['GET'])
def get_user_activity(username):
    """
    Get user activity log and recent actions
    """
    try:
        db = get_dashboard_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        user = db.get_user(username)
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User "{username}" not found'
            }), 404
        
        # Generate activity timeline
        activity_log = []
        
        if user.get('created_at'):
            activity_log.append({
                'action': 'Account Created',
                'timestamp': user.get('created_at').isoformat(),
                'description': 'User account was created',
                'type': 'account'
            })
        
        if user.get('face_updated_at'):
            activity_log.append({
                'action': 'Face Image Enrolled',
                'timestamp': user.get('face_updated_at').isoformat(),
                'description': 'Face biometric data was enrolled',
                'type': 'biometric'
            })
        
        if user.get('fingerprint_updated_at'):
            activity_log.append({
                'action': 'Fingerprint Enrolled',
                'timestamp': user.get('fingerprint_updated_at').isoformat(),
                'description': 'Fingerprint biometric data was enrolled',
                'type': 'biometric'
            })
        
        # Sort by timestamp (most recent first)
        activity_log.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'activity': activity_log,
            'total_activities': len(activity_log),
            'message': f'Activity log retrieved for {username}'
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting activity for {username}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve activity: {str(e)}'
        }), 500

def calculate_enrollment_percentage(user):
    """Calculate biometric enrollment completion percentage"""
    total_biometrics = 2  # Face + Fingerprint
    enrolled_count = 0
    
    if user.get('face_image_id'):
        enrolled_count += 1
    if user.get('fingerprint_template'):
        enrolled_count += 1
    
    return int((enrolled_count / total_biometrics) * 100)

def calculate_account_age(created_at):
    """Calculate account age in days"""
    if not created_at:
        return 0
    
    try:
        if isinstance(created_at, str):
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created_date = created_at
        
        age = datetime.now() - created_date.replace(tzinfo=None)
        return age.days
    except:
        return 0

def calculate_security_score(user):
    """Calculate security score based on biometric enrollment"""
    score = 0
    
    # Base score for account creation
    score += 20
    
    # Score for face image
    if user.get('face_image_id'):
        score += 40
    
    # Score for fingerprint
    if user.get('fingerprint_template'):
        score += 40
    
    # Bonus for complete registration
    if user.get('registration_complete'):
        score += 10
    
    return min(score, 100)  # Cap at 100

def get_last_activity(user):
    """Get the most recent activity timestamp"""
    timestamps = []
    
    if user.get('created_at'):
        timestamps.append(user.get('created_at'))
    if user.get('face_updated_at'):
        timestamps.append(user.get('face_updated_at'))
    if user.get('fingerprint_updated_at'):
        timestamps.append(user.get('fingerprint_updated_at'))
    
    if not timestamps:
        return None
    
    latest = max(timestamps)
    return latest.isoformat() if hasattr(latest, 'isoformat') else str(latest)

def assess_data_quality(user):
    """Assess the quality and completeness of user data"""
    quality_score = 0
    max_score = 5
    
    # Check name
    if user.get('name') and len(user.get('name', '').strip()) > 0:
        quality_score += 1
    
    # Check email
    if user.get('email') and '@' in user.get('email', ''):
        quality_score += 1
    
    # Check phone
    if user.get('phone') and len(user.get('phone', '').strip()) > 0:
        quality_score += 1
    
    # Check face image
    if user.get('face_image_id'):
        quality_score += 1
    
    # Check fingerprint
    if user.get('fingerprint_template'):
        quality_score += 1
    
    percentage = int((quality_score / max_score) * 100)
    
    if percentage >= 90:
        return "Excellent"
    elif percentage >= 70:
        return "Good"
    elif percentage >= 50:
        return "Fair"
    else:
        return "Poor"

# Error handlers
@dashboard_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Dashboard endpoint not found'
    }), 404

@dashboard_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error in dashboard module'
    }), 500

def main():
    """Test dashboard functionality"""
    print("=== Dashboard Module Test ===")
    
    # This would normally be run within Flask app context
    print("Dashboard blueprint registered successfully!")
    print("Available endpoints:")
    print("- GET /api/dashboard/user/<username> - Get user information")
    print("- GET /api/dashboard/photo/<username> - Get user photo")
    print("- GET /api/dashboard/stats/<username> - Get user statistics")
    print("- GET /api/dashboard/activity/<username> - Get user activity log")

if __name__ == "__main__":
    main()
