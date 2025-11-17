# Flask API Server for Face Registration
# This server handles requests from React frontend and triggers face capture

from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
import os
import sys
import io
from PIL import Image

# Add the face capture module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'face', 'capture'))
from face_capture import FaceCapture

# Add the face matching module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'face', 'match'))
from face_match import DatabaseFaceMatcher

# Import MongoDB client
from mongodb_client import get_database

# Import admin blueprint
from admin import admin_bp

# Import dashboard blueprint
from dashboard import dashboard_bp

# Import email service
from mail import get_email_service

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Register admin blueprint
app.register_blueprint(admin_bp)

# Register dashboard blueprint
app.register_blueprint(dashboard_bp)

# Global variables to track capture status
capture_status = {}
face_capture_instance = None

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Face registration API is running"})

@app.route('/api/register', methods=['POST'])
def register_user():
    """
    Start face registration process for a user
    Expects JSON: {"name": "username", "email": "email", "phone": "phone"}
    """
    try:
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({"error": "Name is required"}), 400
        
        user_name = data['name'].strip()
        email = data.get('email', '')
        phone = data.get('phone', '')
        
        if not user_name:
            return jsonify({"error": "Valid name is required"}), 400
        
        # Get database connection
        db = get_database()
        
        # Check if user already exists
        if db.user_exists(user_name):
            return jsonify({"error": f"User '{user_name}' already exists"}), 409
        
        # Create user in MongoDB
        user_id = db.create_user(user_name, email, phone)
        if not user_id:
            return jsonify({"error": "Failed to create user"}), 500
        
        # Initialize capture status
        capture_status[user_name] = {
            "status": "ready",
            "photos_captured": 0,
            "total_photos": 1,
            "message": "Registration session started. Ready for manual capture.",
            "completed": False,
            "error": None
        }
        
        # Send registration email notification
        try:
            email_service = get_email_service()
            if email and email_service.mailjet:
                email_result = email_service.send_registration_email(user_name, email)
                print(f"[INFO] Registration email sent to {email}: {email_result.get('message', 'Success')}")
            else:
                print(f"[INFO] Email service unavailable or no email provided for {user_name}")
        except Exception as e:
            print(f"[WARN] Failed to send registration email: {e}")
            # Don't fail registration if email fails
        
        return jsonify({
            "message": f"Registration session started for {user_name}",
            "user_name": user_name,
            "user_id": user_id,
            "status": "ready"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status/<user_name>', methods=['GET'])
def get_capture_status(user_name):
    """Get the current status of face capture for a user"""
    try:
        if user_name not in capture_status:
            return jsonify({"error": "User not found or capture not started"}), 404
        
        return jsonify(capture_status[user_name])
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/capture', methods=['POST'])
def capture_photo():
    """Handle manual photo capture from frontend"""
    try:
        # Get the uploaded photo and user name
        if 'photo' not in request.files:
            return jsonify({"error": "No photo uploaded"}), 400
        
        user_name = request.form.get('user_name')
        if not user_name:
            return jsonify({"error": "User name is required"}), 400
        
        photo = request.files['photo']
        if photo.filename == '':
            return jsonify({"error": "No photo selected"}), 400
        
        # Check if user session exists
        if user_name not in capture_status:
            return jsonify({"error": "User session not found. Please start registration first."}), 404
        
        # Get database connection
        db = get_database()
        
        # Check if photo already captured
        current_count = capture_status[user_name]["photos_captured"]
        if current_count >= 1:
            return jsonify({"error": "Photo already captured"}), 400
        
        # Read photo data
        photo_data = photo.read()
        
        # Save face image to MongoDB (will automatically create steganographic version if fingerprint key exists)
        success = db.save_face_image(user_name, photo_data, "face_001.jpg")
        
        if not success:
            return jsonify({"error": "Failed to save photo to database"}), 500
        
        # Check if steganographic image was created
        user_data = db.get_user_info(user_name)
        has_stego = user_data.get('has_steganographic_image', False) if user_data else False
        
        if has_stego:
            print(f"[INFO] ✅ Steganographic image automatically created for {user_name}")
        else:
            print(f"[INFO] ℹ️ No steganographic image created for {user_name} (fingerprint key not available yet)")
        
        # Update status
        capture_status[user_name]["photos_captured"] = 1
        capture_status[user_name]["message"] = "Photo 1/1 captured successfully"
        capture_status[user_name]["status"] = "completed"
        capture_status[user_name]["completed"] = True
        
        # Update registration status
        db.update_registration_status(user_name, face_complete=True)
        
        # Send face enrollment completion email
        try:
            user_data = db.get_user_info(user_name)
            if user_data and user_data.get('email'):
                email_service = get_email_service()
                if email_service.mailjet:
                    email_result = email_service.send_enrollment_completion_email(
                        user_name, 
                        user_data['email'], 
                        enrollment_type="Face Recognition"
                    )
                    print(f"[INFO] Face enrollment email sent to {user_data['email']}: {email_result.get('message', 'Success')}")
                else:
                    print(f"[INFO] Email service unavailable for face enrollment notification")
            else:
                print(f"[INFO] No email found for user {user_name}")
        except Exception as e:
            print(f"[WARN] Failed to send face enrollment email: {e}")
            # Don't fail enrollment if email fails
        
        return jsonify({
            "success": True,
            "photos_captured": capture_status[user_name]["photos_captured"],
            "message": capture_status[user_name]["message"],
            "completed": capture_status[user_name].get("completed", False)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/capture-fingerprint', methods=['POST'])
def capture_fingerprint():
    """Handle fingerprint capture from R307 sensor"""
    try:
        data = request.get_json()
        
        if not data or 'user_name' not in data:
            return jsonify({"error": "User name is required"}), 400
        
        user_name = data['user_name'].strip()
        if not user_name:
            return jsonify({"error": "Valid user name is required"}), 400
        
        # Check if user session exists
        if user_name not in capture_status:
            return jsonify({"error": "User session not found. Please complete face registration first."}), 404
        
        # Import and use the fingerprint capture module
        sys.path.append(os.path.join(os.path.dirname(__file__), 'finger', 'capture'))
        from finger_capture import R307FingerCapture
        
        # Initialize fingerprint capture
        finger_capture = R307FingerCapture(port='COM3')
        
        # Capture fingerprint template and save to MongoDB
        template_data = finger_capture.capture_fingerprint_template_data(user_name)
        
        if template_data:
            # Get database connection and save template
            db = get_database()
            success = db.save_fingerprint_template(user_name, template_data)
        else:
            success = False
        
        if success:
            # Update user session status
            capture_status[user_name]["fingerprint_captured"] = True
            capture_status[user_name]["message"] = "Face and fingerprint registration completed successfully!"
            
            # Check if user has face image - if yes, create steganographic version now
            db = get_database()
            user_data = db.get_user_info(user_name)
            
            if user_data and user_data.get('face_image_id') and not user_data.get('has_steganographic_image'):
                print(f"[INFO] User {user_name} has face image but no steganographic version. Creating now...")
                
                try:
                    # Import steganography module
                    from steganography import BiometricSteganography
                    
                    # Get the fingerprint key that was just saved
                    fingerprint_key = user_data.get("fingerprint_key")
                    
                    if fingerprint_key and len(fingerprint_key) == 64:
                        # Get original face image
                        face_image_data = db.get_face_image(user_name)
                        
                        if face_image_data:
                            # Create steganographic image
                            steg = BiometricSteganography()
                            success_steg, stego_data, message = steg.embed_key_in_image(face_image_data, fingerprint_key)
                            
                            if success_steg:
                                # Save steganographic image to GridFS
                                stego_image_id = db.fs.put(
                                    stego_data,
                                    filename=f"{user_name}_steganographic_face_001.jpg",
                                    content_type="image/png",
                                    metadata={
                                        "user_name": user_name,
                                        "type": "face_image_steganographic",
                                        "has_embedded_key": True
                                    }
                                )
                                
                                # Update user document
                                users_collection = db.db.users
                                users_collection.update_one(
                                    {"name": user_name},
                                    {
                                        "$set": {
                                            "face_stego_image_id": stego_image_id,
                                            "has_steganographic_image": True
                                        }
                                    }
                                )
                                
                                print(f"[INFO] ✅ Steganographic image created automatically for existing user: {user_name}")
                            else:
                                print(f"[WARN] Failed to create steganographic image: {message}")
                        else:
                            print(f"[WARN] Could not retrieve face image for {user_name}")
                    else:
                        print(f"[WARN] Invalid fingerprint key for {user_name}")
                        
                except Exception as e:
                    print(f"[ERROR] Failed to create steganographic image: {e}")
                    # Don't fail the fingerprint capture if steganography fails
            
            # Send fingerprint enrollment completion email
            try:
                db = get_database()
                user_data = db.get_user_info(user_name)
                if user_data and user_data.get('email'):
                    email_service = get_email_service()
                    if email_service.mailjet:
                        # Check if both face and fingerprint are now complete
                        enrollment_type = "Complete" if user_data.get('face_complete') else "Fingerprint"
                        email_result = email_service.send_enrollment_completion_email(
                            user_name, 
                            user_data['email'], 
                            enrollment_type=enrollment_type
                        )
                        print(f"[INFO] Fingerprint enrollment email sent to {user_data['email']}: {email_result.get('message', 'Success')}")
                    else:
                        print(f"[INFO] Email service unavailable for fingerprint enrollment notification")
                else:
                    print(f"[INFO] No email found for user {user_name}")
            except Exception as e:
                print(f"[WARN] Failed to send fingerprint enrollment email: {e}")
                # Don't fail enrollment if email fails
            
            return jsonify({
                "success": True,
                "message": "Fingerprint captured and saved as .bin format",
                "fingerprint_captured": True
            })
        else:
            return jsonify({"error": "Failed to capture fingerprint. Please ensure R307 sensor is connected to COM3 and try again."}), 500
        
    except ImportError:
        return jsonify({"error": "Fingerprint capture module not available. Please install pyserial: pip install pyserial"}), 500
    except Exception as e:
        return jsonify({"error": f"Fingerprint capture failed: {str(e)}"}), 500

def run_face_capture(user_name, email, phone):
    """Run face capture in a separate thread"""
    global face_capture_instance
    
    try:
        # Update status
        capture_status[user_name]["status"] = "camera_opening"
        capture_status[user_name]["message"] = "Opening camera..."
        
        # Create face capture instance
        face_capture_instance = FaceCapture()
        
        # Custom capture method for API integration
        success = capture_with_status_updates(user_name)
        
        if success:
            capture_status[user_name]["status"] = "completed"
            capture_status[user_name]["completed"] = True
            capture_status[user_name]["message"] = f"Registration completed successfully! 5 photos saved."
            
            # Save user info (in a real app, you'd save to database)
            save_user_info(user_name, email, phone)
        else:
            capture_status[user_name]["status"] = "failed"
            capture_status[user_name]["error"] = "Face capture failed"
            capture_status[user_name]["message"] = "Registration failed. Please try again."
            
    except Exception as e:
        capture_status[user_name]["status"] = "error"
        capture_status[user_name]["error"] = str(e)
        capture_status[user_name]["message"] = f"Error: {str(e)}"

def capture_with_status_updates(user_name):
    """Modified face capture with status updates"""
    import cv2
    import os
    
    # Create user directory
    save_path = "../dataset/face"
    user_folder = os.path.join(save_path, user_name)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        capture_status[user_name]["error"] = "Could not open camera"
        return False
    
    capture_status[user_name]["status"] = "capturing"
    capture_status[user_name]["message"] = "Camera opened. Position your face in view..."
    
    captured_count = 0
    max_photos = 5
    
    while captured_count < max_photos:
        ret, frame = cap.read()
        if not ret:
            capture_status[user_name]["error"] = "Could not read camera frame"
            break
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_capture_instance.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Draw rectangles around faces and status
        display_frame = frame.copy()
        
        if len(faces) > 0:
            for (x, y, w, h) in faces:
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(display_frame, "Face Detected - Capturing...", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        else:
            cv2.putText(display_frame, "No Face Detected", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Show progress
        progress_text = f"Photos: {captured_count}/{max_photos}"
        cv2.putText(display_frame, progress_text, (50, display_frame.shape[0] - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow(f'Face Registration - {user_name}', display_frame)
        
        # Auto-capture when face is detected
        if len(faces) > 0:
            x, y, w, h = faces[0]
            face_img = frame[y:y+h, x:x+w]
            
            # Generate filename
            filename = f"face_{captured_count + 1:03d}.jpg"
            filepath = os.path.join(user_folder, filename)
            
            # Save the face image
            cv2.imwrite(filepath, face_img)
            captured_count += 1
            
            # Update status
            capture_status[user_name]["photos_captured"] = captured_count
            capture_status[user_name]["message"] = f"Captured photo {captured_count}/5..."
            
            print(f"✓ Captured photo {captured_count}/{max_photos}: {filename}")
            
            # Wait before next capture
            if captured_count < max_photos:
                time.sleep(2)
        
        # Check for quit (ESC key)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key
            break
    
    # Release resources
    cap.release()
    cv2.destroyAllWindows()
    
    return captured_count == max_photos

def save_user_info(user_name, email, phone):
    """Save user information to a file"""
    user_info_path = f"../dataset/{user_name}/user_info.txt"
    with open(user_info_path, 'w') as f:
        f.write(f"Name: {user_name}\n")
        f.write(f"Email: {email}\n")
        f.write(f"Phone: {phone}\n")
        f.write(f"Registration Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

@app.route('/api/users-for-selection', methods=['GET'])
def get_users_for_selection():
    """Get list of registered users for manual selection"""
    try:
        # Get database connection
        db = get_database()
        
        # Get all users with complete registration
        users_collection = db.db.users
        users = users_collection.find(
            {
                "registration_complete": True,
                "face_image_id": {"$ne": None}
            },
            {
                "name": 1, 
                "email": 1, 
                "created_at": 1,
                "_id": 0
            }
        ).sort("name", 1)
        
        user_list = []
        for user in users:
            user_list.append({
                "name": user["name"],
                "email": user.get("email", ""),
                "created_at": user.get("created_at", "").strftime("%Y-%m-%d") if user.get("created_at") else ""
            })
        
        return jsonify({
            "success": True,
            "users": user_list,
            "count": len(user_list),
            "message": f"Found {len(user_list)} registered users"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get user list: {str(e)}"
        }), 500

@app.route('/api/manual-login', methods=['POST'])
def manual_login():
    """Handle manual user login selection"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data:
            return jsonify({"error": "Username is required"}), 400
        
        username = data['username'].strip()
        login_method = data.get('method', 'Manual Selection')
        
        if not username:
            return jsonify({"error": "Valid username is required"}), 400
        
        # Get database connection
        db = get_database()
        
        # Verify user exists and is registered
        user_data = db.get_user_info(username)
        
        if not user_data:
            return jsonify({
                "success": False,
                "error": f"User '{username}' not found in database"
            }), 404
        
        if not user_data.get('registration_complete'):
            return jsonify({
                "success": False,
                "error": f"User '{username}' has not completed registration"
            }), 400
        
        # Send login notification email for manual selection
        try:
            if user_data.get('email'):
                email_service = get_email_service()
                if email_service.mailjet:
                    print(f"[DEBUG] Sending manual login notification to: {user_data['email']}")
                    email_result = email_service.send_login_notification(
                        username, 
                        user_data['email'], 
                        confidence_score=1.0,  # Manual selection = 100% confidence
                        login_method=f"Manual Selection ({login_method})"
                    )
                    print(f"[INFO] Manual login email sent to {user_data['email']}: {email_result.get('message', 'Success')}")
                else:
                    print(f"[INFO] Email service unavailable for manual login notification")
            else:
                print(f"[WARN] No email found for user {username}")
        except Exception as e:
            print(f"[WARN] Failed to send manual login email: {e}")
            # Don't fail login if email fails
        
        return jsonify({
            "success": True,
            "username": username,
            "confidence": 1.0,
            "method": login_method,
            "message": f"Manual login successful for {username}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Manual login failed: {str(e)}"
        }), 500

@app.route('/api/verify-user-identity', methods=['POST'])
def verify_user_identity():
    """Verify if the detected user is correct (yes/no confirmation)"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request data required"}), 400
        
        username = data.get('username', '').strip()
        is_correct = data.get('is_correct', False)
        confidence = data.get('confidence', 0.0)
        
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        if is_correct:
            # User confirmed identity - proceed with login
            db = get_database()
            user_data = db.get_user_info(username)
            
            if user_data and user_data.get('email'):
                email_service = get_email_service()
                if email_service.mailjet:
                    email_result = email_service.send_login_notification(
                        username, 
                        user_data['email'], 
                        confidence_score=confidence,
                        login_method="Face Recognition (Confirmed)"
                    )
                    print(f"[INFO] Confirmed login email sent to {user_data['email']}")
            
            return jsonify({
                "success": True,
                "confirmed": True,
                "username": username,
                "message": f"Identity confirmed for {username}"
            })
        else:
            # User rejected identity - offer manual selection
            return jsonify({
                "success": False,
                "confirmed": False,
                "message": "Identity not confirmed. Please select manually.",
                "show_manual_selection": True
            })
            
    except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Identity verification failed: {str(e)}"
            }), 500

@app.route('/api/users', methods=['GET'])
def get_registered_users():
    """Get list of registered users with fingerprint data"""
    try:
        # Get database connection
        db = get_database()
        
        users = db.get_registered_users()
        
        return jsonify({
            "users": users,
            "count": len(users),
            "message": f"Found {len(users)} registered users with complete biometric data"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/face-match', methods=['POST', 'OPTIONS'])
def match_face():
    """Automatically match face from webcam against database"""
    if request.method == 'OPTIONS':
        # Handle CORS preflight request
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
        
    try:
        # Initialize face matcher
        face_matcher = DatabaseFaceMatcher()
        
        # Perform face matching from webcam
        result = face_matcher.match_face_from_webcam(duration_seconds=10)
        
        if result['success']:
            # Send login notification email
            try:
                username = result['matched_user']
                confidence = result['confidence']
                
                print(f"[DEBUG] Attempting to send login email for user: {username}")
                
                # Get user email from database
                db = get_database()
                user_data = db.get_user_info(username)
                
                print(f"[DEBUG] User data retrieved: {user_data is not None}")
                if user_data:
                    print(f"[DEBUG] User data keys: {list(user_data.keys()) if user_data else 'None'}")
                    print(f"[DEBUG] User email: {user_data.get('email', 'No email field')}")
                
                if user_data and user_data.get('email'):
                    email_service = get_email_service()
                    if email_service.mailjet:
                        print(f"[DEBUG] Sending login notification to: {user_data['email']}")
                        email_result = email_service.send_login_notification(
                            username, 
                            user_data['email'], 
                            confidence_score=confidence,
                            login_method="Face Recognition"
                        )
                        print(f"[INFO] Login email sent to {user_data['email']}: {email_result.get('message', 'Success')}")
                    else:
                        print(f"[INFO] Email service unavailable for login notification")
                else:
                    print(f"[WARN] No email found for user {username} - user_data: {user_data}")
            except Exception as e:
                print(f"[WARN] Failed to send login email: {e}")
                import traceback
                traceback.print_exc()
                # Don't fail login if email fails
            
            return jsonify({
                "success": True,
                "matched_user": result['matched_user'],
                "confidence": result['confidence'],
                "message": result['message']
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error'],
                "message": result.get('message', result['error']),
                "best_confidence": result.get('best_confidence', 0.0),
                "show_manual_selection": True  # Flag to show manual selection option
            }), 400
        
    except Exception as e:
        print(f"[ERROR] Face matching API error: {e}")
        return jsonify({
            "success": False,
            "error": f"Face matching failed: {str(e)}"
        }), 500

@app.route('/api/authenticate', methods=['POST'])
def authenticate_user():
    """Authenticate user using fingerprint matching"""
    try:
        data = request.get_json()
        
        if not data or 'username' not in data:
            return jsonify({"error": "Username is required"}), 400
        
        username = data['username'].strip()
        
        if not username:
            return jsonify({"error": "Valid username is required"}), 400
        
        # Get database connection
        db = get_database()
        
        # Get user data to check authentication method
        user_data = db.get_user_info(username)
        if not user_data:
            return jsonify({
                "success": False,
                "message": f"User '{username}' not found in database"
            }), 404
        
        # Add the fingerprint match module to path
        sys.path.append(os.path.join(os.path.dirname(__file__), 'finger', 'match'))
        from finger_match import R307FingerMatcher
        
        # Create matcher instance
        matcher = R307FingerMatcher()
        
        # Check authentication method
        if user_data.get("fingerprint_algorithm") == "sha256":
            print(f"[INFO] SHA-256 user detected: {username}")
            
            # Get template data (will be None for old format users)
            stored_template = db.get_fingerprint_template(username)
            if stored_template:
                print("[INFO] Using template matching (new SHA-256 format)")
                # Use reliable sensor-based template matching
                success, confidence, message = matcher.authenticate_user_with_template(username, stored_template)
            else:
                print("[INFO] Old SHA-256 format detected - fingerprint template not available for matching")
                return jsonify({
                    "success": False,
                    "message": "Please use face authentication or re-register your fingerprint for the updated system"
                }), 400
                
        else:
            print(f"[INFO] Using legacy template-based authentication for {username}")
            # Get stored fingerprint template for legacy users
            stored_template = db.get_fingerprint_template(username)
            if not stored_template:
                return jsonify({
                    "success": False,
                    "message": "No stored fingerprint template found"
                }), 400
            
            # Authenticate using template matching
            success, confidence, message = matcher.authenticate_user_with_template(username, stored_template)
        
        if success:
            # Send login notification email
            try:
                print(f"[DEBUG] Attempting to send login email for user: {username}")
                
                # Get user email from database
                db = get_database()
                user_data = db.get_user_info(username)
                
                print(f"[DEBUG] User data retrieved: {user_data is not None}")
                if user_data:
                    print(f"[DEBUG] User data keys: {list(user_data.keys()) if user_data else 'None'}")
                    print(f"[DEBUG] User email: {user_data.get('email', 'No email field')}")
                
                if user_data and user_data.get('email'):
                    email_service = get_email_service()
                    if email_service.mailjet:
                        print(f"[DEBUG] Sending login notification to: {user_data['email']}")
                        email_result = email_service.send_login_notification(
                            username, 
                            user_data['email'], 
                            confidence_score=confidence/100.0,  # Convert to percentage
                            login_method="Fingerprint Authentication"
                        )
                        print(f"[INFO] Login email sent to {user_data['email']}: {email_result.get('message', 'Success')}")
                    else:
                        print(f"[INFO] Email service unavailable for login notification")
                else:
                    print(f"[WARN] No email found for user {username} - user_data: {user_data}")
            except Exception as e:
                print(f"[WARN] Failed to send login email: {e}")
                import traceback
                traceback.print_exc()
                # Don't fail login if email fails
            
            return jsonify({
                "success": True,
                "username": username,
                "confidence": confidence,
                "message": message
            })
        else:
            return jsonify({
                "success": False,
                "username": username,
                "confidence": confidence,
                "message": message
            }), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-email/<username>', methods=['GET'])
def test_email_for_user(username):
    """Test email sending for a specific user"""
    try:
        # Get user email from database
        db = get_database()
        user_data = db.get_user_info(username)
        
        print(f"[DEBUG] Testing email for user: {username}")
        print(f"[DEBUG] User data retrieved: {user_data is not None}")
        
        if user_data:
            print(f"[DEBUG] User data: {user_data}")
            email = user_data.get('email')
            
            if email:
                email_service = get_email_service()
                if email_service.mailjet:
                    # Send test login notification
                    email_result = email_service.send_login_notification(
                        username, 
                        email, 
                        confidence_score=0.95,
                        login_method="Manual Test"
                    )
                    return jsonify({
                        "success": True,
                        "message": f"Test email sent to {email}",
                        "email_result": email_result
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Email service not available"
                    }), 500
            else:
                return jsonify({
                    "success": False,
                    "error": f"No email found for user {username}"
                }), 404
        else:
            return jsonify({
                "success": False,
                "error": f"User {username} not found in database"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error testing email: {str(e)}"
        }), 500

if __name__ == '__main__':
    print("=== Face Registration API Server ===")
    print("Server starting on http://localhost:5000")
    print("Health check: http://localhost:5000/api/health")
    print("Test email: http://localhost:5000/api/test-email/<username>")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
