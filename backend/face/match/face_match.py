#!/usr/bin/env python3
"""
Advanced Face Matching for Biometric Authentication System
Uses the trained Siamese Network model from Face Recognition module
Matches faces against the 'new' folder for automatic user identification
"""

import cv2
import numpy as np
import os
import sys
import tempfile
import traceback

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add Face Recognition directory to path for FaceRecognizer import
# Resolve the path properly - from backend/face/match/ go up to project root
_current_file_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(os.path.dirname(_current_file_dir))  # backend/
_project_root = os.path.dirname(_backend_dir)  # Biometric_Data_Encryption/
FACE_RECOGNITION_DIR = os.path.join(_project_root, 'Face Recognition')
sys.path.append(FACE_RECOGNITION_DIR)

print(f"[DEBUG] Face Recognition directory: {FACE_RECOGNITION_DIR}")
print(f"[DEBUG] Directory exists: {os.path.exists(FACE_RECOGNITION_DIR)}")

from mongodb_client import get_database

# Import FaceRecognizer from predict_face.py
try:
    from predict_face import FaceRecognizer
    FACE_RECOGNIZER_AVAILABLE = True
    print("[INFO] FaceRecognizer loaded from predict_face.py")
except ImportError as e:
    print(f"[WARNING] Could not import FaceRecognizer: {e}")
    FACE_RECOGNIZER_AVAILABLE = False


class DatabaseFaceMatcher:
    """Face matcher using trained Siamese Network model"""
    
    def __init__(self):
        self.face_cascade = None
        self.db = None
        self.face_recognizer = None
        self.database_loaded = False
        
        # Paths for Face Recognition module
        self.model_path = os.path.join(FACE_RECOGNITION_DIR, 'face_embeddings_model.keras')
        self.database_dir = os.path.join(FACE_RECOGNITION_DIR, 'new')
        
        # Initialize face detection
        self.setup_face_detection()
        
        # Connect to database
        self.connect_database()
        
        # Initialize FaceRecognizer
        self.setup_face_recognizer()
    
    def setup_face_detection(self):
        """Setup face detection using OpenCV Haar Cascades or MediaPipe"""
        try:
            # Try MediaPipe first (if available)
            try:
                import mediapipe as mp
                self.mp_face_detection = mp.solutions.face_detection
                self.face_detector = self.mp_face_detection.FaceDetection(
                    model_selection=0, min_detection_confidence=0.7
                )
                print("[INFO] Using MediaPipe for face detection")
                return
            except ImportError:
                pass
            
            # Fallback to OpenCV Haar Cascades
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            print("[INFO] Using OpenCV Haar Cascades for face detection")
            
        except Exception as e:
            print(f"[ERROR] Failed to setup face detection: {e}")
            raise
    
    def connect_database(self):
        """Connect to MongoDB database"""
        try:
            self.db = get_database()
            if not self.db.client:
                raise Exception("Could not connect to database")
            print("[INFO] Connected to MongoDB database")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            raise
    
    def setup_face_recognizer(self):
        """Initialize the FaceRecognizer from predict_face.py"""
        try:
            if not FACE_RECOGNIZER_AVAILABLE:
                print("[WARNING] FaceRecognizer not available, falling back to basic matching")
                return
            
            # Resolve absolute paths
            model_path = os.path.abspath(self.model_path)
            database_dir = os.path.abspath(self.database_dir)
            
            print(f"[DEBUG] Resolved model path: {model_path}")
            print(f"[DEBUG] Resolved database dir: {database_dir}")
            
            # Check if model exists
            if not os.path.exists(model_path):
                print(f"[WARNING] Model not found at {model_path}")
                # Try to find the model in common locations
                alt_paths = [
                    os.path.join(_project_root, 'Face Recognition', 'face_embeddings_model.keras'),
                    os.path.join(os.path.dirname(_backend_dir), 'Face Recognition', 'face_embeddings_model.keras'),
                ]
                for alt_path in alt_paths:
                    if os.path.exists(alt_path):
                        model_path = alt_path
                        print(f"[INFO] Found model at alternate path: {model_path}")
                        break
                else:
                    print(f"[ERROR] Could not find model in any location")
                    return
            
            # Check if database directory exists
            if not os.path.exists(database_dir):
                print(f"[WARNING] Database directory not found at {database_dir}")
                os.makedirs(database_dir, exist_ok=True)
                print(f"[INFO] Created database directory: {database_dir}")
            
            # Initialize FaceRecognizer
            print(f"[INFO] Initializing FaceRecognizer...")
            print(f"[INFO] Model path: {model_path}")
            print(f"[INFO] Database dir: {database_dir}")
            
            self.face_recognizer = FaceRecognizer(
                model_path=model_path,
                database_dir=database_dir
            )
            
            print("[INFO] FaceRecognizer initialized successfully")
            
        except Exception as e:
            print(f"[ERROR] Failed to setup FaceRecognizer: {e}")
            traceback.print_exc()
            self.face_recognizer = None
    
    def load_database_faces(self):
        """Build the face embeddings database from the 'new' folder"""
        try:
            if self.face_recognizer is None:
                print("[ERROR] FaceRecognizer not initialized")
                return False
            
            # Check if there are any images in the database directory
            image_files = [f for f in os.listdir(self.database_dir) 
                          if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            if len(image_files) == 0:
                print(f"[WARNING] No images found in {self.database_dir}")
                return False
            
            print(f"[INFO] Found {len(image_files)} images in database directory")
            
            # Build the database
            self.face_recognizer.build_database()
            self.database_loaded = True
            
            print(f"[INFO] Database built with {len(self.face_recognizer.embeddings_db)} people")
            return len(self.face_recognizer.embeddings_db) > 0
            
        except Exception as e:
            print(f"[ERROR] Failed to load database faces: {e}")
            traceback.print_exc()
            return False
    
    def detect_faces(self, image):
        """Detect faces in image"""
        faces = []
        
        try:
            if hasattr(self, 'face_detector') and self.face_detector is not None:
                # Use MediaPipe
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = self.face_detector.process(rgb_image)
                
                if results.detections:
                    h, w, _ = image.shape
                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box
                        x = int(bbox.xmin * w)
                        y = int(bbox.ymin * h)
                        width = int(bbox.width * w)
                        height = int(bbox.height * h)
                        # Ensure positive values
                        x = max(0, x)
                        y = max(0, y)
                        faces.append((x, y, width, height))
            else:
                # Use OpenCV Haar Cascades
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                detected = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                faces = [(x, y, w, h) for (x, y, w, h) in detected]
        except Exception as e:
            print(f"[ERROR] Face detection error: {e}")
        
        return faces
    
    def save_temp_face_image(self, face_image):
        """Save face image to a temporary file for FaceRecognizer"""
        try:
            # Create a temporary file
            fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(fd)
            
            # Save the face image
            cv2.imwrite(temp_path, face_image)
            
            return temp_path
        except Exception as e:
            print(f"[ERROR] Failed to save temp face image: {e}")
            return None
    
    def match_face_from_webcam(self, duration_seconds=10):
        """Capture from webcam and try to match face using trained Siamese Network model"""
        try:
            print("[INFO] Starting webcam for face matching...")
            
            # Check if FaceRecognizer is available
            if self.face_recognizer is None:
                return {"success": False, "error": "Face recognition model not available. Please ensure the model is trained."}
            
            # Try different camera indices if primary fails
            cap = None
            camera_indices = [0, 1, 2]
            
            for index in camera_indices:
                print(f"[INFO] Trying camera index {index}...")
                cap = cv2.VideoCapture(index)
                
                # Set camera properties for better performance
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if cap.isOpened():
                    # Test if we can actually read frames
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        print(f"[INFO] Successfully initialized camera {index}")
                        break
                    else:
                        print(f"[WARNING] Camera {index} opened but no frames available")
                        cap.release()
                        cap = None
                else:
                    print(f"[WARNING] Camera {index} failed to open")
                    cap = None
            
            if cap is None or not cap.isOpened():
                return {"success": False, "error": "Could not access any webcam. Please check camera permissions and availability."}
            
            # Load database faces (build embeddings from 'new' folder)
            if not self.database_loaded:
                if not self.load_database_faces():
                    cap.release()
                    return {"success": False, "error": "No face images found in database. Please register users first."}
            
            best_match = None
            best_confidence = 0.0
            frame_count = 0
            max_frames = duration_seconds * 30  # Assume 30 FPS
            
            # Recognition threshold (for cosine similarity, higher is better)
            recognition_threshold = 0.6
            
            print(f"[INFO] Face matching started. Looking for faces for {duration_seconds} seconds...")
            
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    print("[WARNING] Failed to read frame from camera")
                    break
                
                # Check if frame is valid
                if frame is None or frame.size == 0:
                    print("[WARNING] Invalid frame received")
                    continue
                
                frame_count += 1
                
                # Process every 5th frame for better performance
                if frame_count % 5 != 0:
                    # Display frame with current best match
                    try:
                        display_frame = frame.copy()
                        
                        if best_match:
                            cv2.putText(display_frame, f"Best Match: {best_match} ({best_confidence:.2f})", 
                                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        else:
                            cv2.putText(display_frame, "Looking for faces...", 
                                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        
                        cv2.putText(display_frame, f"Time remaining: {duration_seconds - frame_count//30}s", 
                                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
                        cv2.putText(display_frame, "Press 'q' to quit", 
                                   (10, display_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        
                        cv2.imshow('Face Matching', display_frame)
                        
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            print("[INFO] User pressed 'q' to quit")
                            break
                    except Exception as e:
                        print(f"[WARNING] Display error: {e}")
                    continue
                
                # Detect faces
                try:
                    faces = self.detect_faces(frame)
                except Exception as e:
                    print(f"[ERROR] Face detection failed: {e}")
                    faces = []
                
                for face_bbox in faces:
                    try:
                        x, y, w, h = face_bbox
                        
                        # Validate bounding box
                        if w <= 0 or h <= 0:
                            continue
                        
                        # Extract face region with padding
                        padding = 20
                        y_start = max(0, y - padding)
                        y_end = min(frame.shape[0], y + h + padding)
                        x_start = max(0, x - padding)
                        x_end = min(frame.shape[1], x + w + padding)
                        
                        face_region = frame[y_start:y_end, x_start:x_end]
                        
                        if face_region.size == 0:
                            continue
                        
                        # Save face to temp file for prediction
                        temp_path = self.save_temp_face_image(face_region)
                        if temp_path is None:
                            continue
                        
                        try:
                            # Use FaceRecognizer to predict
                            result = self.face_recognizer.predict(
                                temp_path, 
                                threshold=recognition_threshold,
                                top_k=3,
                                use_cosine=True
                            )
                            
                            if 'error' not in result and result.get('is_recognized', False):
                                confidence = result.get('confidence_distance', 0)
                                predicted_name = result.get('predicted_name', 'Unknown')
                                
                                # For cosine similarity, higher is better
                                if confidence > best_confidence:
                                    best_match = predicted_name
                                    best_confidence = confidence
                                    print(f"[INFO] New best match: {best_match} (confidence: {best_confidence:.3f})")
                            
                        finally:
                            # Clean up temp file
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        
                    except Exception as e:
                        print(f"[ERROR] Face processing error: {e}")
                        continue
                
                # Display current frame with detection
                try:
                    display_frame = frame.copy()
                    
                    # Draw face rectangles
                    for (x, y, w, h) in faces:
                        cv2.rectangle(display_frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    
                    # Display current best match
                    if best_match:
                        cv2.putText(display_frame, f"Best Match: {best_match} ({best_confidence:.2f})", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    else:
                        cv2.putText(display_frame, "Looking for faces...", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    
                    cv2.putText(display_frame, f"Time remaining: {duration_seconds - frame_count//30}s", 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    cv2.putText(display_frame, "Press 'q' to quit", 
                               (10, display_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    cv2.imshow('Face Matching', display_frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("[INFO] User pressed 'q' to quit")
                        break
                        
                except Exception as e:
                    print(f"[WARNING] Display error: {e}")
            
            cap.release()
            cv2.destroyAllWindows()
            
            # Check if we found a match
            if best_match and best_confidence >= recognition_threshold:
                return {
                    "success": True,
                    "matched_user": best_match,
                    "confidence": float(best_confidence),
                    "message": f"Face matched with {best_match} (confidence: {best_confidence:.2f})"
                }
            else:
                return {
                    "success": False,
                    "error": "User not found - no matching face in database",
                    "best_confidence": float(best_confidence) if best_confidence > 0 else 0.0,
                    "message": "No registered user matches your face. Please register first or try manual selection."
                }
                
        except Exception as e:
            print(f"[ERROR] Face matching error: {e}")
            traceback.print_exc()
            if 'cap' in locals():
                cap.release()
            cv2.destroyAllWindows()
            return {"success": False, "error": f"Face matching failed: {str(e)}"}
    
    def match_single_frame(self, frame):
        """Match face in a single frame (for API use)"""
        try:
            # Check if FaceRecognizer is available
            if self.face_recognizer is None:
                return {"success": False, "error": "Face recognition model not available"}
            
            # Load database faces if not already loaded
            if not self.database_loaded:
                if not self.load_database_faces():
                    return {"success": False, "error": "No face images in database"}
            
            # Detect faces
            faces = self.detect_faces(frame)
            
            if len(faces) == 0:
                return {"success": False, "error": "No faces detected in frame"}
            
            best_match = None
            best_confidence = 0.0
            recognition_threshold = 0.6
            
            for face_bbox in faces:
                x, y, w, h = face_bbox
                
                # Extract face region with padding
                padding = 20
                y_start = max(0, y - padding)
                y_end = min(frame.shape[0], y + h + padding)
                x_start = max(0, x - padding)
                x_end = min(frame.shape[1], x + w + padding)
                
                face_region = frame[y_start:y_end, x_start:x_end]
                
                if face_region.size == 0:
                    continue
                
                # Save face to temp file for prediction
                temp_path = self.save_temp_face_image(face_region)
                if temp_path is None:
                    continue
                
                try:
                    # Use FaceRecognizer to predict
                    result = self.face_recognizer.predict(
                        temp_path, 
                        threshold=recognition_threshold,
                        top_k=3,
                        use_cosine=True
                    )
                    
                    if 'error' not in result and result.get('is_recognized', False):
                        confidence = result.get('confidence_distance', 0)
                        predicted_name = result.get('predicted_name', 'Unknown')
                        
                        if confidence > best_confidence:
                            best_match = predicted_name
                            best_confidence = confidence
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            if best_match and best_confidence >= recognition_threshold:
                return {
                    "success": True,
                    "matched_user": best_match,
                    "confidence": float(best_confidence),
                    "bbox": faces[0]  # Return first face bounding box
                }
            else:
                return {
                    "success": False,
                    "error": "User not found - no matching face in database",
                    "best_confidence": float(best_confidence) if best_confidence > 0 else 0.0,
                    "message": "No registered user matches your face. Please register first or try manual selection."
                }
                
        except Exception as e:
            print(f"[ERROR] Single frame matching error: {e}")
            traceback.print_exc()
            return {"success": False, "error": f"Face matching failed: {str(e)}"}


def main():
    """Test face matching functionality"""
    print("=== Database Face Matcher Test (Using Siamese Network) ===")
    
    try:
        matcher = DatabaseFaceMatcher()
        result = matcher.match_face_from_webcam(duration_seconds=15)
        
        print("\n=== Face Matching Result ===")
        print(f"Success: {result['success']}")
        
        if result['success']:
            print(f"Matched User: {result['matched_user']}")
            print(f"Confidence: {result['confidence']:.3f}")
            print(f"Message: {result['message']}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            if 'best_confidence' in result:
                print(f"Best Confidence: {result['best_confidence']:.3f}")
                
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
