#!/usr/bin/env python3
"""
Admin Module for Biometric Authentication System
Provides administrative functionality for user management
"""

from flask import Blueprint, request, jsonify
from mongodb_client import get_database
import gridfs
from bson import ObjectId
from datetime import datetime

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def get_admin_database():
    """Get database instance for admin operations"""
    return get_database()

@admin_bp.route('/users', methods=['GET'])
def get_all_users():
    """
    Get all registered users with their complete details
    Returns all user information including biometric data status
    """
    try:
        db = get_admin_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        # Get all users from database
        users_collection = db.db.users
        users_cursor = users_collection.find({})
        
        users_list = []
        for user in users_cursor:
            # Convert ObjectId to string for JSON serialization
            user_data = {
                '_id': str(user.get('_id', '')),
                'name': user.get('name', ''),
                'email': user.get('email', ''),
                'phone': user.get('phone', ''),
                'created_at': user.get('created_at', '').isoformat() if user.get('created_at') else None,
                'face_image_id': str(user.get('face_image_id', '')) if user.get('face_image_id') else None,
                'fingerprint_template': bool(user.get('fingerprint_template')),  # Don't send actual template
                'registration_complete': user.get('registration_complete', False),
                'face_updated_at': user.get('face_updated_at', '').isoformat() if user.get('face_updated_at') else None,
                'fingerprint_updated_at': user.get('fingerprint_updated_at', '').isoformat() if user.get('fingerprint_updated_at') else None
            }
            users_list.append(user_data)
        
        return jsonify({
            'success': True,
            'users': users_list,
            'total_count': len(users_list),
            'message': f'Retrieved {len(users_list)} users successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting all users: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to retrieve users: {str(e)}'
        }), 500

@admin_bp.route('/users/<username>', methods=['DELETE'])
def delete_user(username):
    """
    Delete a user and all their biometric data
    This includes user record, face images in GridFS, and fingerprint templates
    """
    try:
        db = get_admin_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        users_collection = db.db.users
        
        # First, get user data to retrieve face image ID
        user = users_collection.find_one({"name": username})
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User "{username}" not found'
            }), 404
        
        # Delete face image from GridFS if exists
        if user.get('face_image_id'):
            try:
                db.fs.delete(user['face_image_id'])
                print(f"✅ Deleted face image for user: {username}")
            except Exception as e:
                print(f"⚠️ Could not delete face image: {e}")
        
        # Delete user record
        result = users_collection.delete_one({"name": username})
        
        if result.deleted_count > 0:
            print(f"✅ User deleted: {username}")
            return jsonify({
                'success': True,
                'message': f'User "{username}" and all biometric data deleted successfully',
                'deleted_count': result.deleted_count
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to delete user "{username}"'
            }), 500
            
    except Exception as e:
        print(f"❌ Error deleting user {username}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to delete user: {str(e)}'
        }), 500

@admin_bp.route('/users/<username>/details', methods=['GET'])
def get_user_details(username):
    """
    Get detailed information about a specific user
    Includes all registration data and biometric status
    """
    try:
        db = get_admin_database()
        
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
        
        # Prepare detailed user information
        user_details = {
            '_id': str(user.get('_id', '')),
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'created_at': user.get('created_at', '').isoformat() if user.get('created_at') else None,
            'registration_complete': user.get('registration_complete', False),
            'biometric_data': {
                'face_image': {
                    'exists': bool(user.get('face_image_id')),
                    'image_id': str(user.get('face_image_id', '')) if user.get('face_image_id') else None,
                    'updated_at': user.get('face_updated_at', '').isoformat() if user.get('face_updated_at') else None
                },
                'fingerprint': {
                    'exists': bool(user.get('fingerprint_template')),
                    'template_length': len(user.get('fingerprint_template', '')) if user.get('fingerprint_template') else 0,
                    'updated_at': user.get('fingerprint_updated_at', '').isoformat() if user.get('fingerprint_updated_at') else None
                }
            }
        }
        
        return jsonify({
            'success': True,
            'user': user_details,
            'message': f'Retrieved details for user "{username}"'
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting user details for {username}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get user details: {str(e)}'
        }), 500

@admin_bp.route('/stats', methods=['GET'])
def get_admin_stats():
    """
    Get administrative statistics about the biometric system
    """
    try:
        db = get_admin_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        users_collection = db.db.users
        
        # Get total user count
        total_users = users_collection.count_documents({})
        
        # Get complete registration count
        complete_registrations = users_collection.count_documents({
            'registration_complete': True,
            'face_image_id': {'$ne': None},
            'fingerprint_template': {'$ne': None}
        })
        
        # Get incomplete registrations
        incomplete_registrations = total_users - complete_registrations
        
        # Get users with only face data
        face_only = users_collection.count_documents({
            'face_image_id': {'$ne': None},
            'fingerprint_template': None
        })
        
        # Get users with only fingerprint data
        fingerprint_only = users_collection.count_documents({
            'face_image_id': None,
            'fingerprint_template': {'$ne': None}
        })
        
        # Get GridFS statistics
        fs_files = db.db['fs.files']
        total_images = fs_files.count_documents({'metadata.type': 'face_image'})
        
        stats = {
            'users': {
                'total': total_users,
                'complete_registration': complete_registrations,
                'incomplete_registration': incomplete_registrations,
                'face_only': face_only,
                'fingerprint_only': fingerprint_only
            },
            'biometric_data': {
                'total_face_images': total_images,
                'total_fingerprint_templates': users_collection.count_documents({
                    'fingerprint_template': {'$ne': None}
                })
            },
            'database_info': {
                'database_name': db.database_name,
                'collections': db.db.list_collection_names(),
                'last_updated': datetime.now().isoformat()
            }
        }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'message': 'Administrative statistics retrieved successfully'
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting admin stats: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get statistics: {str(e)}'
        }), 500

@admin_bp.route('/cleanup', methods=['POST'])
def cleanup_orphaned_data():
    """
    Clean up orphaned data in the database
    Removes GridFS files without corresponding user records
    """
    try:
        db = get_admin_database()
        
        if not db.client:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        users_collection = db.db.users
        fs_files = db.db['fs.files']
        
        # Get all user face image IDs
        users_with_images = users_collection.find(
            {'face_image_id': {'$ne': None}},
            {'face_image_id': 1}
        )
        
        valid_image_ids = set()
        for user in users_with_images:
            valid_image_ids.add(user['face_image_id'])
        
        # Find orphaned GridFS files
        all_files = fs_files.find({'metadata.type': 'face_image'})
        orphaned_files = []
        
        for file_doc in all_files:
            if file_doc['_id'] not in valid_image_ids:
                orphaned_files.append(file_doc['_id'])
        
        # Delete orphaned files
        deleted_count = 0
        for file_id in orphaned_files:
            try:
                db.fs.delete(file_id)
                deleted_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete orphaned file {file_id}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'Cleanup completed. Deleted {deleted_count} orphaned files.',
            'deleted_files': deleted_count,
            'total_orphaned': len(orphaned_files)
        }), 200
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return jsonify({
            'success': False,
            'error': f'Cleanup failed: {str(e)}'
        }), 500

# Error handlers
@admin_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Admin endpoint not found'
    }), 404

@admin_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error in admin module'
    }), 500

def main():
    """Test admin functionality"""
    print("=== Admin Module Test ===")
    
    # This would normally be run within Flask app context
    print("Admin blueprint registered successfully!")
    print("Available endpoints:")
    print("- GET /api/admin/users - Get all users")
    print("- DELETE /api/admin/users/<username> - Delete user")
    print("- GET /api/admin/users/<username>/details - Get user details")
    print("- GET /api/admin/stats - Get system statistics")
    print("- POST /api/admin/cleanup - Clean orphaned data")

if __name__ == "__main__":
    main()
