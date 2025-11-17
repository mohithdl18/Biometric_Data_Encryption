#!/usr/bin/env python3
"""
MongoDB Atlas Integration for Biometric Authentication System
Handles user registration, face image storage, and fingerprint template storage
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import gridfs
import base64
import os
from datetime import datetime
from bson import ObjectId
import io

class BiometricDatabase:
    def __init__(self):
        """Initialize MongoDB Atlas connection"""
        # MongoDB Atlas connection string (replace with your actual connection string)
        self.connection_string = "string"
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
        """Save face image to GridFS and update user record"""
        try:
            users_collection = self.db.users
            
            # Save image to GridFS
            image_id = self.fs.put(
                image_data,
                filename=f"{user_name}_{filename}",
                content_type="image/jpeg",
                metadata={"user_name": user_name, "type": "face_image"}
            )
            
            # Update user record with image ID
            result = users_collection.update_one(
                {"name": user_name},
                {
                    "$set": {
                        "face_image_id": image_id,
                        "face_updated_at": datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ Face image saved for user: {user_name}")
                return True
            else:
                print(f"❌ Failed to update user record for: {user_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving face image: {e}")
            return False
    
    def save_fingerprint_template(self, user_name, template_data):
        """Save fingerprint template to user record"""
        try:
            users_collection = self.db.users
            
            # Convert binary template to base64 for storage
            template_b64 = base64.b64encode(template_data).decode('utf-8')
            
            result = users_collection.update_one(
                {"name": user_name},
                {
                    "$set": {
                        "fingerprint_template": template_b64,
                        "fingerprint_updated_at": datetime.now(),
                        "registration_complete": True
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ Fingerprint template saved for user: {user_name}")
                return True
            else:
                print(f"❌ Failed to save fingerprint template for: {user_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error saving fingerprint template: {e}")
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
        """Get face image for a user"""
        try:
            user = self.get_user(user_name)
            if not user or not user.get("face_image_id"):
                return None
            
            image_file = self.fs.get(user["face_image_id"])
            return image_file.read()
            
        except Exception as e:
            print(f"❌ Error getting face image: {e}")
            return None
    
    def get_fingerprint_template(self, user_name):
        """Get fingerprint template for a user"""
        try:
            user = self.get_user(user_name)
            if not user or not user.get("fingerprint_template"):
                return None
            
            # Convert base64 back to binary
            template_data = base64.b64decode(user["fingerprint_template"])
            return template_data
            
        except Exception as e:
            print(f"❌ Error getting fingerprint template: {e}")
            return None
    
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
    """Test MongoDB connection and operations"""
    print("=== MongoDB Atlas Biometric Database Test ===")
    
    # Connect to database
    db = get_database()
    
    if not db.client:
        print("❌ Cannot connect to database")
        return
    
    # Test operations
    print("\n1. Testing user creation...")
    user_id = db.create_user("TestUser", "test@example.com", "1234567890")
    
    print("\n2. Testing user retrieval...")
    user = db.get_user("TestUser")
    if user:
        print(f"✅ User found: {user['name']}")
    
    print("\n3. Testing registered users list...")
    users = db.get_registered_users()
    print(f"Registered users: {users}")
    
    # Cleanup
    db.disconnect()
    print("\n✅ Database test completed!")

if __name__ == "__main__":
    main()
