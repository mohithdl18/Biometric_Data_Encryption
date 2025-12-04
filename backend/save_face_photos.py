#!/usr/bin/env python3
"""
Save Face Photos Module
Downloads user face photos from MongoDB and saves them to the Face Recognition/new folder
with the naming format: USERNAME_0001.jpg, USERNAME_0002.jpg, USERNAME_0003.jpg
"""

import os
from mongodb_client import get_database

# Path to save face photos for face recognition training
FACE_RECOGNITION_NEW_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 
    "Face Recognition", 
    "new"
)

def format_username_for_filename(username):
    """
    Format username for filename by replacing spaces with underscores
    Example: "MOHITH D L" -> "MOHITH_D_L"
    """
    return username.strip().replace(" ", "_")

def save_user_photos_to_new_folder(username):
    """
    Download all face photos for a user from MongoDB and save them to Face Recognition/new folder
    
    Args:
        username (str): The username to download photos for
        
    Returns:
        dict: Result with success status, saved files count, and message
    """
    try:
        # Ensure the target folder exists
        if not os.path.exists(FACE_RECOGNITION_NEW_FOLDER):
            os.makedirs(FACE_RECOGNITION_NEW_FOLDER)
            print(f"✅ Created folder: {FACE_RECOGNITION_NEW_FOLDER}")
        
        # Get database connection
        db = get_database()
        
        if not db or not db.client:
            return {
                "success": False,
                "saved_count": 0,
                "message": "Failed to connect to database"
            }
        
        # Get all face images for the user
        face_images = db.get_all_face_images(username)
        
        if not face_images:
            return {
                "success": False,
                "saved_count": 0,
                "message": f"No face images found for user: {username}"
            }
        
        # Format username for filename
        formatted_name = format_username_for_filename(username)
        
        saved_count = 0
        saved_files = []
        
        # Save each image with the correct naming format
        for i, image_data in enumerate(face_images):
            # Generate filename: USERNAME_0001.jpg, USERNAME_0002.jpg, etc.
            photo_number = i + 1
            filename = f"{formatted_name}_{photo_number:04d}.jpg"
            filepath = os.path.join(FACE_RECOGNITION_NEW_FOLDER, filename)
            
            try:
                # Write image data to file
                with open(filepath, 'wb') as f:
                    f.write(image_data)
                
                saved_count += 1
                saved_files.append(filename)
                print(f"✅ Saved: {filename}")
                
            except Exception as e:
                print(f"❌ Failed to save {filename}: {e}")
        
        if saved_count > 0:
            return {
                "success": True,
                "saved_count": saved_count,
                "saved_files": saved_files,
                "message": f"Successfully saved {saved_count} photos for {username} to {FACE_RECOGNITION_NEW_FOLDER}"
            }
        else:
            return {
                "success": False,
                "saved_count": 0,
                "message": f"Failed to save any photos for {username}"
            }
            
    except Exception as e:
        print(f"❌ Error saving photos for {username}: {e}")
        return {
            "success": False,
            "saved_count": 0,
            "message": f"Error: {str(e)}"
        }

def save_single_photo_to_new_folder(username, image_data, photo_number):
    """
    Save a single face photo to Face Recognition/new folder
    Called immediately after each photo capture
    
    Args:
        username (str): The username
        image_data (bytes): The image data to save
        photo_number (int): The photo number (1, 2, or 3)
        
    Returns:
        dict: Result with success status and message
    """
    try:
        # Ensure the target folder exists
        if not os.path.exists(FACE_RECOGNITION_NEW_FOLDER):
            os.makedirs(FACE_RECOGNITION_NEW_FOLDER)
            print(f"✅ Created folder: {FACE_RECOGNITION_NEW_FOLDER}")
        
        # Format username for filename
        formatted_name = format_username_for_filename(username)
        
        # Generate filename: USERNAME_0001.jpg, USERNAME_0002.jpg, etc.
        filename = f"{formatted_name}_{photo_number:04d}.jpg"
        filepath = os.path.join(FACE_RECOGNITION_NEW_FOLDER, filename)
        
        # Write image data to file
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        print(f"✅ Saved to Face Recognition/new: {filename}")
        
        return {
            "success": True,
            "filename": filename,
            "filepath": filepath,
            "message": f"Successfully saved {filename}"
        }
        
    except Exception as e:
        print(f"❌ Error saving photo {photo_number} for {username}: {e}")
        return {
            "success": False,
            "filename": None,
            "message": f"Error: {str(e)}"
        }

def main():
    """Test the save photos functionality"""
    print("=== Save Face Photos Test ===")
    
    # Test with an existing user
    test_username = input("Enter username to download photos for: ").strip()
    
    if not test_username:
        print("❌ Please enter a valid username")
        return
    
    result = save_user_photos_to_new_folder(test_username)
    
    print(f"\nResult: {result}")

if __name__ == "__main__":
    main()
