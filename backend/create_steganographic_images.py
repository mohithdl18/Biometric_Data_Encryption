#!/usr/bin/env python3
"""
Utility Script: Create Steganographic Images for Existing Users
This script processes existing users who have both face images and fingerprint keys
but don't have steganographic images yet.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from mongodb_client import get_database
from steganography import BiometricSteganography

def create_steganographic_for_existing_users():
    """
    Find users with face images and fingerprint keys but no steganographic images.
    Create and save steganographic images for them.
    """
    print("=" * 60)
    print("🎭 Steganographic Image Generator for Existing Users")
    print("=" * 60)
    
    db = get_database()
    if not db.client:
        print("❌ Failed to connect to database")
        return
    
    # Find users with face and fingerprint but no steganographic image
    users_collection = db.db.users
    
    query = {
        "face_image_id": {"$exists": True},
        "fingerprint_algorithm": "sha256",
        "$or": [
            {"has_steganographic_image": {"$exists": False}},
            {"has_steganographic_image": False},
            {"face_stego_image_id": {"$exists": False}}
        ]
    }
    
    users_needing_stego = list(users_collection.find(query))
    
    print(f"\n📊 Found {len(users_needing_stego)} users needing steganographic images:\n")
    
    if len(users_needing_stego) == 0:
        print("✅ All users already have steganographic images or don't need them!")
        return
    
    # List users
    for i, user in enumerate(users_needing_stego, 1):
        print(f"{i}. {user['name']}")
        print(f"   - Has face: ✅")
        print(f"   - Has fingerprint: ✅")
        print(f"   - Has stego image: ❌")
        print()
    
    # Ask for confirmation
    response = input("Do you want to create steganographic images for these users? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Operation cancelled.")
        return
    
    print("\n" + "=" * 60)
    print("🔄 Processing users...")
    print("=" * 60 + "\n")
    
    steg = BiometricSteganography()
    success_count = 0
    error_count = 0
    
    for user in users_needing_stego:
        username = user['name']
        print(f"\n📝 Processing: {username}")
        print("-" * 40)
        
        try:
            # Get fingerprint key
            fingerprint_key = user.get("fingerprint_key") or user.get("fingerprint_template")
            
            if not fingerprint_key or len(fingerprint_key) != 64:
                print(f"❌ No valid fingerprint key found for {username}")
                error_count += 1
                continue
            
            print(f"✅ Found fingerprint key: {fingerprint_key[:8]}...{fingerprint_key[-8:]}")
            
            # Get original face image
            face_image_data = db.get_face_image(username)
            
            if not face_image_data:
                print(f"❌ No face image found for {username}")
                error_count += 1
                continue
            
            print(f"✅ Retrieved face image ({len(face_image_data)} bytes)")
            
            # Create steganographic image
            print("🎭 Embedding fingerprint key into image...")
            success, stego_data, message = steg.embed_key_in_image(face_image_data, fingerprint_key)
            
            if not success:
                print(f"❌ Failed to create steganographic image: {message}")
                error_count += 1
                continue
            
            print(f"✅ Steganographic image created ({len(stego_data)} bytes)")
            
            # Save steganographic image to GridFS
            print("💾 Saving to database...")
            stego_image_id = db.fs.put(
                stego_data,
                filename=f"{username}_steganographic_face_001.jpg",
                content_type="image/png",
                metadata={
                    "user_name": username,
                    "type": "face_image_steganographic",
                    "has_embedded_key": True
                }
            )
            
            # Update user document
            users_collection.update_one(
                {"name": username},
                {
                    "$set": {
                        "face_stego_image_id": stego_image_id,
                        "has_steganographic_image": True
                    }
                }
            )
            
            print(f"✅ Steganographic image saved for {username}")
            print(f"   - Image ID: {stego_image_id}")
            
            # Verify the embedded key
            print("🔍 Verifying embedded key...")
            verification = steg.verify_key_in_image(stego_data, fingerprint_key)
            
            if verification:
                print("✅ Key verification successful!")
                success_count += 1
            else:
                print("⚠️ Warning: Key verification failed!")
                error_count += 1
            
        except Exception as e:
            print(f"❌ Error processing {username}: {e}")
            error_count += 1
    
    # Final summary
    print("\n" + "=" * 60)
    print("📊 Processing Complete!")
    print("=" * 60)
    print(f"✅ Successfully processed: {success_count} users")
    print(f"❌ Errors encountered: {error_count} users")
    print(f"📝 Total processed: {len(users_needing_stego)} users")
    print("=" * 60)

def list_steganographic_images():
    """List all users with steganographic images"""
    print("\n" + "=" * 60)
    print("📋 Users with Steganographic Images")
    print("=" * 60 + "\n")
    
    db = get_database()
    if not db.client:
        print("❌ Failed to connect to database")
        return
    
    users_collection = db.db.users
    
    users_with_stego = list(users_collection.find({
        "has_steganographic_image": True,
        "face_stego_image_id": {"$exists": True}
    }))
    
    if len(users_with_stego) == 0:
        print("No users have steganographic images yet.")
        return
    
    print(f"Found {len(users_with_stego)} users with steganographic images:\n")
    
    for i, user in enumerate(users_with_stego, 1):
        print(f"{i}. {user['name']}")
        print(f"   - Face Image ID: {user.get('face_image_id')}")
        print(f"   - Stego Image ID: {user.get('face_stego_image_id')}")
        print(f"   - Fingerprint Key: {user.get('fingerprint_key', '')[:8]}...{user.get('fingerprint_key', '')[-8:]}")
        print()

def main():
    """Main menu"""
    print("\n" + "=" * 60)
    print("🎭 Steganographic Image Management Tool")
    print("=" * 60)
    print("\nOptions:")
    print("1. Create steganographic images for existing users")
    print("2. List users with steganographic images")
    print("3. Exit")
    print()
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        create_steganographic_for_existing_users()
    elif choice == "2":
        list_steganographic_images()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
