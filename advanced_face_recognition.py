import cv2
import numpy as np
import os
import onnxruntime as ort
from sklearn.metrics.pairwise import cosine_similarity
import requests
import urllib.request
from pathlib import Path

# --- Configuration ---
KNOWN_IMAGE_PATH = "mohith.jpg"
MODEL_DIR = "models"

class AdvancedFaceRecognizer:
    def __init__(self):
        self.face_detector = None
        self.face_recognizer = None
        self.known_encodings = []
        self.known_names = []
        
        # Create models directory
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        # Initialize models
        self.setup_models()
    
    def download_file(self, url, filename):
        """Download a file if it doesn't exist"""
        filepath = os.path.join(MODEL_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[INFO] Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filepath)
                print(f"[INFO] Downloaded {filename}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to download {filename}: {e}")
                return False
        return True
    
    def setup_models(self):
        """Setup face detection and recognition models"""
        try:
            # Try to use MediaPipe for face detection (fallback)
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
            print("[INFO] Using MediaPipe for face detection and feature extraction")
            
        except ImportError:
            print("[WARNING] MediaPipe not available, using OpenCV Haar Cascades")
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
    
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
        
        return np.array(features)
    
    def extract_lbp_features(self, gray_image):
        """Extract Local Binary Pattern features"""
        from skimage.feature import local_binary_pattern
        
        # LBP parameters
        radius = 1
        n_points = 8 * radius
        
        lbp = local_binary_pattern(gray_image, n_points, radius, method='uniform')
        
        # Calculate histogram
        hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, 
                              range=(0, n_points + 2), density=True)
        
        return hist
    
    def extract_hog_features(self, gray_image):
        """Extract HOG features"""
        from skimage.feature import hog
        
        features = hog(gray_image, orientations=9, pixels_per_cell=(8, 8),
                      cells_per_block=(2, 2), block_norm='L2-Hys')
        
        return features
    
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
        except:
            pass
        
        return None
    
    def load_known_face(self, image_path, name):
        """Load and encode a known face"""
        try:
            print(f"[INFO] Loading known face: {image_path}")
            
            image = cv2.imread(image_path)
            if image is None:
                print(f"[ERROR] Could not load {image_path}")
                return False
            
            # Detect face
            faces = self.detect_faces(image)
            
            if len(faces) == 0:
                print(f"[ERROR] No faces found in {image_path}")
                return False
            
            # Use the largest face
            face_bbox = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = face_bbox
            
            # Extract face region with some padding
            padding = 20
            face_region = image[max(0, y-padding):min(image.shape[0], y+h+padding),
                               max(0, x-padding):min(image.shape[1], x+w+padding)]
            
            # Extract features
            features = self.extract_deep_features(face_region)
            
            self.known_encodings.append(features)
            self.known_names.append(name)
            
            print(f"[INFO] Successfully loaded face for {name} with {len(features)} features")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load known face: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def detect_faces(self, image):
        """Detect faces in image"""
        faces = []
        
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
        
        return faces
    
    def recognize_faces(self, frame):
        """Recognize faces in frame"""
        try:
            faces = self.detect_faces(frame)
            results = []
            
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
                
                name = "Unknown"
                confidence = 0.0
                
                if len(self.known_encodings) > 0:
                    # Compare with known faces
                    similarities = []
                    for known_encoding in self.known_encodings:
                        # Ensure same length
                        min_len = min(len(features), len(known_encoding))
                        similarity = cosine_similarity([features[:min_len]], 
                                                     [known_encoding[:min_len]])[0][0]
                        similarities.append(similarity)
                    
                    best_idx = np.argmax(similarities)
                    best_similarity = similarities[best_idx]
                    
                    # Threshold for recognition
                    if best_similarity > 0.7:  # Adjusted threshold
                        name = self.known_names[best_idx]
                        confidence = best_similarity
                
                results.append({
                    'bbox': (x, y, w, h),
                    'name': name,
                    'confidence': confidence
                })
            
            return results
            
        except Exception as e:
            print(f"[ERROR] Face recognition error: {e}")
            return []

# Initialize advanced face recognizer
print("[INFO] Initializing Advanced Face Recognizer...")
recognizer = AdvancedFaceRecognizer()

# Load known face
known_name = os.path.splitext(KNOWN_IMAGE_PATH)[0]
success = recognizer.load_known_face(KNOWN_IMAGE_PATH, known_name)

if not success:
    print("[WARNING] Could not load known face. Continuing with detection only...")

# Start webcam
print("[INFO] Starting webcam...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("[ERROR] Could not open webcam")
    exit(1)

print("[INFO] Advanced Face Recognition Started!")
print("[INFO] Press 'q' to quit")

frame_count = 0
recognition_interval = 5  # Process every 5th frame for better performance

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame from webcam.")
            break
        
        frame_count += 1
        
        # Process every nth frame
        if frame_count % recognition_interval == 0:
            # Recognize faces
            results = recognizer.recognize_faces(frame)
            
            # Store results for display
            if hasattr(recognizer, 'last_results'):
                recognizer.last_results = results
            else:
                recognizer.last_results = results
        
        # Display results (use last computed results for smooth display)
        if hasattr(recognizer, 'last_results'):
            for result in recognizer.last_results:
                x, y, w, h = result['bbox']
                name = result['name']
                confidence = result['confidence']
                
                # Choose color
                if name != "Unknown":
                    color = (0, 255, 0)  # Green for known
                    label = f"{name} ({confidence:.2f})"
                else:
                    color = (0, 0, 255)  # Red for unknown
                    label = "Unknown"
                
                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                # Draw label
                cv2.rectangle(frame, (x, y-30), (x+w, y), color, cv2.FILLED)
                cv2.putText(frame, label, (x+5, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Print status
                if frame_count % 150 == 0:  # Print every 150 frames
                    print(f"[INFO] Detected: {label}")
        
        # Display frame
        cv2.imshow('Advanced Face Recognition', frame)
        
        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\n[INFO] Interrupted by user")
except Exception as e:
    print(f"[ERROR] An error occurred: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Advanced Face Recognition application closed")
