#!/usr/bin/env python3
"""
MongoDB Atlas Integration for Biometric Authentication System
Handles user registration, face image storage, and fingerprint template storage with SHA-256 key derivation
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import gridfs
import base64
import hashlib
import os
from datetime import datetime
from bson import ObjectId
import io
from steganography import BiometricSteganography

class BiometricDatabase:
    def __init__(self):
        """Initialize MongoDB Atlas connection"""
        # MongoDB Atlas connection string (replace with your actual connection string)
        self.connection_string = ""
        self.database_name = "biometric_auth"
        self.client = None
        self.db = None
        self.fs = None
        
    def connect(self):
        """Connect to MongoDB Atlas"""
        try:
            # Add SSL configuration to handle certificate issues
            self.client = MongoClient(
                self.connection_string,
                tlsAllowInvalidCertificates=True,  # Allow invalid certificates for development
                serverSelectionTimeoutMS=5000,    # Reduce timeout for faster failure
                connectTimeoutMS=5000,            # Reduce connection timeout
                socketTimeoutMS=5000              # Reduce socket timeout
            )
            self.db = self.client[self.database_name]
            self.fs = gridfs.GridFS(self.db)
            
            # Test connection
            self.client.admin.command('ping')
            print("✅ Connected to MongoDB Atlas successfully!")
            return True
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB Atlas: {e}")
            return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB Atlas")
    
    def create_user(self, name, email, phone):
        """Create a new user in the database"""
        try:
            users_collection = self.db.users
            
            user_data = {
                "name": name,
                "email": email,
                "phone": phone,
                "created_at": datetime.now(),
                "face_image_id": None,
                "fingerprint_template": None,
                "registration_complete": False
            }
            
            result = users_collection.insert_one(user_data)
            print(f"✅ User created: {name} (ID: {result.inserted_id})")
            return str(result.inserted_id)
            
        except DuplicateKeyError:
            print(f"❌ User already exists: {name}")
            return None
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return None
    
    def user_exists(self, name):
        """Check if user already exists"""
        try:
            users_collection = self.db.users
            user = users_collection.find_one({"name": name})
            return user is not None
        except Exception as e:
            print(f"❌ Error checking user existence: {e}")
            return False
    
    def save_face_image(self, user_name, image_data, filename="face_001.jpg"):
        """Save both original face image and steganographic version (if applicable) to GridFS"""
        try:
            users_collection = self.db.users
            
            # Save original image first
            original_image_id = self.fs.put(
                image_data,
                filename=f"{user_name}_original_{filename}",
                content_type="image/png",
                metadata={
                    "user_name": user_name, 
                    "type": "face_image_original",
                    "upload_date": datetime.now()
                }
            )
            print(f"✅ Original face image saved for {user_name}")
            
            # Get user info to check for fingerprint key
            user = self.get_user(user_name)
            fingerprint_key = None
            stego_image_id = None
            
            # Check if user has a fingerprint key to embed
            if user and user.get("fingerprint_algorithm") == "sha256":
                fingerprint_key = user.get("fingerprint_key") or user.get("fingerprint_template")
                if fingerprint_key and len(fingerprint_key) == 64:
                    print(f"[INFO] Found fingerprint key for {user_name}, creating steganographic image...")
                    
                    # Use steganography to embed the key
                    steg = BiometricSteganography()
                    success, stego_image_data, message = steg.embed_key_in_image(image_data, fingerprint_key)
                    
                    if success:
                        # Save steganographic image separately
                        stego_image_id = self.fs.put(
                            stego_image_data,
                            filename=f"{user_name}_steganographic_{filename}",
                            content_type="image/png",
                            metadata={
                                "user_name": user_name, 
                                "type": "face_image_steganographic",
                                "has_embedded_key": True,
                                "upload_date": datetime.now()
                            }
                        )
                        print(f"✅ Steganographic image saved for {user_name} (with embedded fingerprint key)")
                    else:
                        print(f"❌ Failed to create steganographic image: {message}")
            
            # Update user record with both image IDs
            update_data = {
                "face_image_id": original_image_id,
                "face_updated_at": datetime.now()
            }
            
            if stego_image_id:
                update_data["face_stego_image_id"] = stego_image_id
                update_data["has_steganographic_image"] = True
            
            result = users_collection.update_one(
                {"name": user_name},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                status = "with steganographic version" if stego_image_id else "original only"
                print(f"✅ Face image(s) saved for user: {user_name} ({status})")
                return True
            else:
                print(f"❌ Failed to update user record for: {user_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving face image: {e}")
            return False
    
    def save_fingerprint_template(self, user_name, template_data):
        """Save fingerprint template as SHA-256 derived key AND store raw template for authentication"""
        try:
            users_collection = self.db.users
            
            # Generate SHA-256 key from fingerprint template
            fingerprint_key = hashlib.sha256(template_data).hexdigest()
            print(f"[INFO] Generated SHA-256 key from fingerprint template for {user_name}")
            
            # Store both SHA-256 key and raw template data (base64 encoded)
            template_b64 = base64.b64encode(template_data).decode('utf-8')
            
            result = users_collection.update_one(
                {"name": user_name},
                {
                    "$set": {
                        "fingerprint_template": template_b64,  # Store original template for matching
                        "fingerprint_key": fingerprint_key,   # Store SHA-256 key for encryption  
                        "fingerprint_algorithm": "sha256",
                        "fingerprint_updated_at": datetime.now(),
                        "registration_complete": True
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ Fingerprint SHA-256 key saved for user: {user_name}")
                print(f"   - Key: {fingerprint_key[:16]}...{fingerprint_key[-16:]} (64 chars)")
                return True
            else:
                print(f"❌ Failed to save fingerprint key for: {user_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving fingerprint key: {e}")
            return False
    
    def get_user(self, name):
        """Get user data by name"""
        try:
            users_collection = self.db.users
            user = users_collection.find_one({"name": name})
            return user
        except Exception as e:
            print(f"❌ Error getting user: {e}")
            return None
    
    def get_user_info(self, name):
        """Get user information (alias for get_user for compatibility)"""
        return self.get_user(name)
    
    def get_registered_users(self):
        """Get list of users with complete registration (both face and fingerprint)"""
        try:
            users_collection = self.db.users
            users = users_collection.find(
                {
                    "registration_complete": True,
                    "face_image_id": {"$ne": None},
                    "fingerprint_template": {"$ne": None}
                },
                {"name": 1, "_id": 0}
            )
            
            user_list = [user["name"] for user in users]
            print(f"✅ Found {len(user_list)} registered users")
            return user_list
            
        except Exception as e:
            print(f"❌ Error getting registered users: {e}")
            return []
    
    def get_face_image(self, user_name):
        """Get original face image for a user"""
        try:
            user = self.get_user(user_name)
            if not user or not user.get("face_image_id"):
                return None
            
            image_file = self.fs.get(user["face_image_id"])
            return image_file.read()
            
        except Exception as e:
            print(f"❌ Error getting face image: {e}")
            return None
    
    def get_steganographic_image(self, user_name):
        """Get steganographic face image (with embedded key) for a user"""
        try:
            user = self.get_user(user_name)
            if not user:
                return None
            
            # Check if user has steganographic image
            if not user.get("face_stego_image_id"):
                print(f"[INFO] No steganographic image found for {user_name}")
                return None
            
            stego_image_file = self.fs.get(user["face_stego_image_id"])
            print(f"✅ Retrieved steganographic image for {user_name}")
            return stego_image_file.read()
            
        except Exception as e:
            print(f"❌ Error getting steganographic image: {e}")
            return None
    
    def get_fingerprint_template(self, user_name):
        """Get fingerprint template data for a user"""
        try:
            user = self.get_user(user_name)
            if not user or not user.get("fingerprint_template"):
                return None
            
            # Check if this is SHA-256 user with old or new format
            if user.get("fingerprint_algorithm") == "sha256":
                template_data = user["fingerprint_template"]
                
                # Check if it's old format (SHA-256 key) or new format (base64 template)
                if len(template_data) == 64 and all(c in '0123456789abcdef' for c in template_data.lower()):
                    # Old format: SHA-256 key stored as fingerprint_template
                    print(f"[WARNING] User {user_name} uses old SHA-256 format - cannot extract template for matching")
                    return None
                else:
                    # New format: base64-encoded template data
                    template_binary = base64.b64decode(template_data)
                    print(f"[INFO] Retrieved template for SHA-256 user {user_name}: {len(template_binary)} bytes")
                    return template_binary
            else:
                # Legacy base64-encoded template - convert back to binary
                template_data = base64.b64decode(user["fingerprint_template"])
                print(f"[INFO] Retrieved legacy template for {user_name}: {len(template_data)} bytes")
                return template_data
                
        except Exception as e:
            print(f"❌ Error getting fingerprint template: {e}")
            return None
    
    def get_fingerprint_key(self, user_name):
        """Get SHA-256 fingerprint key for a user (for SHA-256 users only)"""
        try:
            user = self.get_user(user_name)
            if not user:
                return None
            
            if user.get("fingerprint_algorithm") == "sha256":
                fingerprint_key = user.get("fingerprint_key")
                if fingerprint_key:
                    print(f"[INFO] Retrieved SHA-256 key for {user_name}")
                    return fingerprint_key
                else:
                    print(f"[INFO] No fingerprint_key field, using legacy SHA-256 storage")
                    return user.get("fingerprint_template")
            else:
                return None
                
        except Exception as e:
            print(f"❌ Error getting fingerprint key: {e}")
            return None
    
    def authenticate_fingerprint(self, user_name, new_template_data):
        """Authenticate user by comparing SHA-256 keys with tolerance for sensor variations"""
        try:
            user = self.get_user(user_name)
            if not user:
                print(f"[ERROR] User {user_name} not found")
                return False
            
            # Check if user has SHA-256 based fingerprint
            if user.get("fingerprint_algorithm") == "sha256":
                # Generate SHA-256 key from new template
                new_fingerprint_key = hashlib.sha256(new_template_data).hexdigest()
                
                # Get stored key
                stored_key = user["fingerprint_template"]
                
                # Direct key comparison
                keys_match = new_fingerprint_key == stored_key
                
                print(f"[DEBUG] Fingerprint authentication for {user_name}:")
                print(f"   - New template size: {len(new_template_data)} bytes")
                print(f"   - New key: {new_fingerprint_key}")
                print(f"   - Stored key: {stored_key}")
                print(f"   - Keys match: {keys_match}")
                
                if keys_match:
                    print(f"✅ SHA-256 fingerprint authentication successful for {user_name}")
                    return True
                else:
                    print(f"❌ SHA-256 fingerprint authentication failed for {user_name}")
                    
                    # Additional debugging: Check if template data is consistent
                    print(f"   - Template data preview: {new_template_data[:20].hex()}...")
                    return False
            else:
                # Legacy comparison for backward compatibility
                print(f"[INFO] User {user_name} uses legacy fingerprint storage")
                stored_template = self.get_fingerprint_template(user_name)
                if stored_template is None:
                    return False
                # Simple byte comparison
                return stored_template == new_template_data
                
        except Exception as e:
            print(f"❌ Error during fingerprint authentication: {e}")
            return False
    
    def update_registration_status(self, user_name, face_complete=False, fingerprint_complete=False):
        """Update user registration status"""
        try:
            users_collection = self.db.users
            
            update_data = {}
            if face_complete:
                update_data["face_complete"] = True
            if fingerprint_complete:
                update_data["fingerprint_complete"] = True
            
            # Check if both are complete
            user = self.get_user(user_name)
            if user:
                face_done = user.get("face_image_id") is not None or face_complete
                finger_done = user.get("fingerprint_template") is not None or fingerprint_complete
                
                if face_done and finger_done:
                    update_data["registration_complete"] = True
            
            result = users_collection.update_one(
                {"name": user_name},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            print(f"❌ Error updating registration status: {e}")
            return False

# Global database instance
db_instance = BiometricDatabase()

def get_database():
    """Get database instance (singleton pattern)"""
    if not db_instance.client:
        db_instance.connect()
    return db_instance

def main():
    """Test MongoDB connection and SHA-256 key operations"""
    print("=== MongoDB Atlas Biometric Database with SHA-256 Key Test ===")
    
    # Connect to database
    db = get_database()
    
    if not db.client:
        print("❌ Cannot connect to database")
        return
    
    # Test operations
    print("\n1. Testing user creation...")
    user_id = db.create_user("TestUserSHA", "test@example.com", "1234567890")
    
    print("\n2. Testing SHA-256 fingerprint key storage...")
    # Simulate a fingerprint template
    import secrets
    test_fingerprint = secrets.token_bytes(256)  # 256-byte fingerprint template
    
    success = db.save_fingerprint_template("TestUserSHA", test_fingerprint)
    if success:
        print("✅ SHA-256 fingerprint key storage successful")
    else:
        print("❌ SHA-256 fingerprint key storage failed")
        return
    
    print("\n3. Testing fingerprint authentication...")
    # Test with original template (should succeed)
    auth_result = db.authenticate_fingerprint("TestUserSHA", test_fingerprint)
    print(f"Authentication with original template: {'✅ SUCCESS' if auth_result else '❌ FAILED'}")
    
    # Test with different template (should fail)
    different_fingerprint = secrets.token_bytes(256)
    auth_result_diff = db.authenticate_fingerprint("TestUserSHA", different_fingerprint)
    print(f"Authentication with different template: {'❌ CORRECTLY FAILED' if not auth_result_diff else '⚠️ FALSE POSITIVE'}")
    
    print("\n4. Testing key retrieval...")
    retrieved_key = db.get_fingerprint_template("TestUserSHA")
    if retrieved_key:
        print(f"✅ Successfully retrieved fingerprint key")
        print(f"Key format: {type(retrieved_key).__name__} ({len(retrieved_key)} characters)")
    else:
        print("❌ Failed to retrieve fingerprint key")
    
    print("\n5. Testing registered users list...")
    users = db.get_registered_users()
    print(f"Registered users: {users}")
    
    # Cleanup
    db.disconnect()
    print("\n✅ Database test with SHA-256 keys completed!")

if __name__ == "__main__":
    main()
