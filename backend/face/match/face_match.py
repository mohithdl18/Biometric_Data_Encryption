#!/usr/bin/env python3
"""
Advanced Face Matching for Biometric Authentication System
Matches faces against MongoDB database for automatic user identification
"""

import cv2
import numpy as np
import os
import sys
from sklearn.metrics.pairwise import cosine_similarity
import io
from PIL import Image

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from mongodb_client import get_database

class DatabaseFaceMatcher:
    def __init__(self):
        self.face_cascade = None
        self.known_encodings = []
        self.known_names = []
        self.db = None
        
        # Initialize face detection
        self.setup_face_detection()
        
        # Connect to database
        self.connect_database()
    
    def setup_face_detection(self):
        """Setup face detection using OpenCV Haar Cascades"""
        try:
            # Try MediaPipe first (if available)
            try:
                import mediapipe as mp
                self.mp_face_detection = mp.solutions.face_detection
                self.mp_face_mesh = mp.solutions.face_mesh
                
                self.face_detector = self.mp_face_detection.FaceDetection(
                    model_selection=0, min_detection_confidence=0.7
                )
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    static_image_mode=False, 
                    max_num_faces=10,
                    refine_landmarks=True, 
                    min_detection_confidence=0.7
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
    
    def extract_deep_features(self, face_image):
        """Extract deep features from face using multiple methods"""
        features = []
        
        # Convert to grayscale
        if len(face_image.shape) == 3:
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_image
        
        # Resize to standard size
        gray = cv2.resize(gray, (112, 112))
        
        try:
            # Method 1: LBP (Local Binary Patterns)
            lbp = self.extract_lbp_features(gray)
            features.extend(lbp)
            
            # Method 2: HOG (Histogram of Oriented Gradients) 
            hog = self.extract_hog_features(gray)
            features.extend(hog)
            
            # Method 3: Gabor filters
            gabor = self.extract_gabor_features(gray)
            features.extend(gabor)
            
            # Method 4: MediaPipe landmarks (if available)
            if hasattr(self, 'face_mesh'):
                landmarks = self.extract_mediapipe_features(face_image)
                if landmarks is not None:
                    features.extend(landmarks)
        except Exception as e:
            print(f"[WARNING] Feature extraction error: {e}")
            # Fallback to basic features if advanced methods fail
            features = gray.flatten()[:1000].tolist()  # Simple pixel features
        
        return np.array(features)
    
    def extract_lbp_features(self, gray_image):
        """Extract Local Binary Pattern features"""
        try:
            from skimage.feature import local_binary_pattern
            
            # LBP parameters
            radius = 1
            n_points = 8 * radius
            
            lbp = local_binary_pattern(gray_image, n_points, radius, method='uniform')
            
            # Calculate histogram
            hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, 
                                  range=(0, n_points + 2), density=True)
            
            return hist
        except ImportError:
            # Fallback if scikit-image not available
            return self.extract_simple_features(gray_image)
    
    def extract_hog_features(self, gray_image):
        """Extract HOG features"""
        try:
            from skimage.feature import hog
            
            features = hog(gray_image, orientations=9, pixels_per_cell=(8, 8),
                          cells_per_block=(2, 2), block_norm='L2-Hys')
            
            return features
        except ImportError:
            # Fallback if scikit-image not available
            return self.extract_simple_features(gray_image)
    
    def extract_gabor_features(self, gray_image):
        """Extract Gabor filter features"""
        features = []
        
        # Multiple Gabor kernels
        for theta in range(0, 180, 45):  # 4 orientations
            for frequency in [0.1, 0.3]:  # 2 frequencies
                kernel = cv2.getGaborKernel((21, 21), 5, np.radians(theta), 
                                          2*np.pi*frequency, 0.5, 0, ktype=cv2.CV_32F)
                filtered = cv2.filter2D(gray_image, cv2.CV_8UC3, kernel)
                features.extend([filtered.mean(), filtered.std()])
        
        return features
    
    def extract_mediapipe_features(self, face_image):
        """Extract MediaPipe facial landmarks"""
        try:
            if not hasattr(self, 'face_mesh'):
                return None
                
            rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_image)
            
            if results.multi_face_landmarks:
                landmarks = results.multi_face_landmarks[0]
                features = []
                
                # Extract key landmark points
                for i in [1, 33, 61, 199, 291, 405]:  # Key facial points
                    if i < len(landmarks.landmark):
                        lm = landmarks.landmark[i]
                        features.extend([lm.x, lm.y, lm.z])
                
                return features
        except Exception:
            pass
        
        return None
    
    def extract_simple_features(self, gray_image):
        """Simple feature extraction fallback"""
        # Basic statistical features
        features = [
            gray_image.mean(),
            gray_image.std(),
            gray_image.min(),
            gray_image.max()
        ]
        
        # Add histogram features
        hist = cv2.calcHist([gray_image], [0], None, [256], [0, 256])
        features.extend(hist.flatten()[:50])  # First 50 histogram bins
        
        return features
    
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
                        faces.append((x, y, width, height))
            else:
                # Use OpenCV Haar Cascades
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                detected = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                faces = [(x, y, w, h) for (x, y, w, h) in detected]
        except Exception as e:
            print(f"[ERROR] Face detection error: {e}")
        
        return faces
    
    def load_database_faces(self):
        """Load all face encodings from MongoDB database"""
        try:
            print("[INFO] Loading face encodings from database...")
            
            # Get all users with face images
            users_collection = self.db.db.users
            users_with_faces = users_collection.find({
                'face_image_id': {'$ne': None},
                'registration_complete': True
            })
            
            self.known_encodings = []
            self.known_names = []
            
            for user in users_with_faces:
                try:
                    # Get face image from GridFS
                    face_image_data = self.db.get_face_image(user['name'])
                    
                    if face_image_data is None:
                        print(f"[WARNING] No face image found for {user['name']}")
                        continue
                    
                    # Convert image data to OpenCV format
                    image_array = np.frombuffer(face_image_data, np.uint8)
                    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                    
                    if image is None:
                        print(f"[WARNING] Could not decode image for {user['name']}")
                        continue
                    
                    # Detect face in the image
                    faces = self.detect_faces(image)
                    
                    if len(faces) == 0:
                        print(f"[WARNING] No faces detected in image for {user['name']}")
                        continue
                    
                    # Use the largest face
                    face_bbox = max(faces, key=lambda f: f[2] * f[3])
                    x, y, w, h = face_bbox
                    
                    # Extract face region with padding
                    padding = 20
                    face_region = image[max(0, y-padding):min(image.shape[0], y+h+padding),
                                       max(0, x-padding):min(image.shape[1], x+w+padding)]
                    
                    if face_region.size == 0:
                        continue
                    
                    # Extract features
                    features = self.extract_deep_features(face_region)
                    
                    self.known_encodings.append(features)
                    self.known_names.append(user['name'])
                    
                    print(f"[INFO] Loaded face encoding for {user['name']} ({len(features)} features)")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to process face for {user['name']}: {e}")
                    continue
            
            print(f"[INFO] Loaded {len(self.known_encodings)} face encodings from database")
            return len(self.known_encodings) > 0
            
        except Exception as e:
            print(f"[ERROR] Failed to load database faces: {e}")
            return False
    
    def match_face_from_webcam(self, duration_seconds=10):
        """Capture from webcam and try to match face"""
        try:
            print("[INFO] Starting webcam for face matching...")
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                return {"success": False, "error": "Could not access webcam"}
            
            # Load database faces
            if not self.load_database_faces():
                cap.release()
                return {"success": False, "error": "No face encodings found in database"}
            
            best_match = None
            best_confidence = 0.0
            frame_count = 0
            max_frames = duration_seconds * 30  # Assume 30 FPS
            
            print(f"[INFO] Face matching started. Looking for faces for {duration_seconds} seconds...")
            
            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Process every 10th frame for performance
                if frame_count % 10 != 0:
                    # Display frame with current best match
                    display_frame = frame.copy()
                    
                    if best_match:
                        cv2.putText(display_frame, f"Best Match: {best_match} ({best_confidence:.2f})", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    else:
                        cv2.putText(display_frame, "Looking for faces...", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    
                    cv2.putText(display_frame, f"Time remaining: {duration_seconds - frame_count//30}s", 
                               (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    cv2.imshow('Face Matching', display_frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    continue
                
                # Detect faces
                faces = self.detect_faces(frame)
                
                for face_bbox in faces:
                    x, y, w, h = face_bbox
                    
                    # Extract face region
                    padding = 10
                    face_region = frame[max(0, y-padding):min(frame.shape[0], y+h+padding),
                                      max(0, x-padding):min(frame.shape[1], x+w+padding)]
                    
                    if face_region.size == 0:
                        continue
                    
                    # Extract features
                    features = self.extract_deep_features(face_region)
                    
                    # Compare with known faces
                    for i, known_encoding in enumerate(self.known_encodings):
                        try:
                            # Ensure same length
                            min_len = min(len(features), len(known_encoding))
                            if min_len == 0:
                                continue
                                
                            similarity = cosine_similarity([features[:min_len]], 
                                                         [known_encoding[:min_len]])[0][0]
                            
                            # Update best match if this is better
                            if similarity > best_confidence and similarity > 0.7:  # Threshold
                                best_match = self.known_names[i]
                                best_confidence = similarity
                                
                        except Exception as e:
                            print(f"[WARNING] Comparison error: {e}")
                            continue
                
                # Display current frame with detection
                display_frame = frame.copy()
                
                # Draw face rectangles
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                
                # Display current best match
                if best_match:
                    cv2.putText(display_frame, f"Best Match: {best_match} ({best_confidence:.2f})", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    cv2.putText(display_frame, "Looking for faces...", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                cv2.putText(display_frame, f"Time remaining: {duration_seconds - frame_count//30}s", 
                           (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                cv2.imshow('Face Matching', display_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            cap.release()
            cv2.destroyAllWindows()
            
            if best_match and best_confidence > 0.7:
                return {
                    "success": True,
                    "matched_user": best_match,
                    "confidence": float(best_confidence),
                    "message": f"Face matched with {best_match} (confidence: {best_confidence:.2f})"
                }
            else:
                return {
                    "success": False,
                    "error": "No matching face found",
                    "best_confidence": float(best_confidence) if best_confidence > 0 else 0.0
                }
                
        except Exception as e:
            print(f"[ERROR] Face matching error: {e}")
            if 'cap' in locals():
                cap.release()
            cv2.destroyAllWindows()
            return {"success": False, "error": f"Face matching failed: {str(e)}"}
    
    def match_single_frame(self, frame):
        """Match face in a single frame (for API use)"""
        try:
            # Load database faces if not already loaded
            if len(self.known_encodings) == 0:
                if not self.load_database_faces():
                    return {"success": False, "error": "No face encodings in database"}
            
            # Detect faces
            faces = self.detect_faces(frame)
            
            if len(faces) == 0:
                return {"success": False, "error": "No faces detected in frame"}
            
            best_match = None
            best_confidence = 0.0
            
            for face_bbox in faces:
                x, y, w, h = face_bbox
                
                # Extract face region
                padding = 10
                face_region = frame[max(0, y-padding):min(frame.shape[0], y+h+padding),
                                  max(0, x-padding):min(frame.shape[1], x+w+padding)]
                
                if face_region.size == 0:
                    continue
                
                # Extract features
                features = self.extract_deep_features(face_region)
                
                # Compare with known faces
                for i, known_encoding in enumerate(self.known_encodings):
                    try:
                        # Ensure same length
                        min_len = min(len(features), len(known_encoding))
                        if min_len == 0:
                            continue
                            
                        similarity = cosine_similarity([features[:min_len]], 
                                                     [known_encoding[:min_len]])[0][0]
                        
                        # Update best match if this is better
                        if similarity > best_confidence:
                            best_match = self.known_names[i]
                            best_confidence = similarity
                            
                    except Exception as e:
                        print(f"[WARNING] Comparison error: {e}")
                        continue
            
            if best_match and best_confidence > 0.7:  # Threshold
                return {
                    "success": True,
                    "matched_user": best_match,
                    "confidence": float(best_confidence),
                    "bbox": faces[0]  # Return first face bounding box
                }
            else:
                return {
                    "success": False,
                    "error": "No matching face found above threshold",
                    "best_confidence": float(best_confidence) if best_confidence > 0 else 0.0
                }
                
        except Exception as e:
            print(f"[ERROR] Single frame matching error: {e}")
            return {"success": False, "error": f"Face matching failed: {str(e)}"}

def main():
    """Test face matching functionality"""
    print("=== Database Face Matcher Test ===")
    
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
            print(f"Error: {result['error']}")
            if 'best_confidence' in result:
                print(f"Best Confidence: {result['best_confidence']:.3f}")
                
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
