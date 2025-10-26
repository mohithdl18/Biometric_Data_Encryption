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

# Import MongoDB client
from mongodb_client import get_database

# Import admin blueprint
from admin import admin_bp

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Register admin blueprint
app.register_blueprint(admin_bp)

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
        
        # Save face image to MongoDB
        success = db.save_face_image(user_name, photo_data, "face_001.jpg")
        
        if not success:
            return jsonify({"error": "Failed to save photo to database"}), 500
        
        # Update status
        capture_status[user_name]["photos_captured"] = 1
        capture_status[user_name]["message"] = "Photo 1/1 captured successfully"
        capture_status[user_name]["status"] = "completed"
        capture_status[user_name]["completed"] = True
        
        # Update registration status
        db.update_registration_status(user_name, face_complete=True)
        
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
        
        # Get stored fingerprint template
        stored_template = db.get_fingerprint_template(username)
        if not stored_template:
            return jsonify({
                "success": False,
                "message": "No fingerprint template found for user"
            }), 404
        
        # Add the fingerprint match module to path
        sys.path.append(os.path.join(os.path.dirname(__file__), 'finger', 'match'))
        from finger_match import R307FingerMatcher
        
        # Create matcher instance
        matcher = R307FingerMatcher()
        
        # Perform authentication with stored template
        success, confidence, message = matcher.authenticate_user_with_template(username, stored_template)
        
        if success:
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

if __name__ == '__main__':
    print("=== Face Registration API Server ===")
    print("Server starting on http://localhost:5000")
    print("Health check: http://localhost:5000/api/health")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
