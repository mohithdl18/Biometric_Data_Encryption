"""
Real-time Face Recognition Script
Uses webcam for live face detection and recognition using the trained Siamese Network model.
"""

import os
import sys
import cv2
import numpy as np
import argparse
import time
from collections import deque

# Import FaceRecognizer from predict_face.py
from predict_face import FaceRecognizer


class RealtimeFaceRecognizer:
    """Real-time face recognition using webcam."""
    
    def __init__(self, model_path, database_dir, threshold=0.9, use_cosine=True):
        """
        Initialize the real-time face recognizer.
        
        Args:
            model_path: Path to the trained embedding model
            database_dir: Directory containing face database images
            threshold: Recognition threshold
            use_cosine: Use cosine similarity instead of Euclidean distance
        """
        self.threshold = threshold
        self.use_cosine = use_cosine
        
        # Initialize the face recognizer
        print("Initializing Face Recognition System...")
        self.recognizer = FaceRecognizer(model_path, database_dir)
        
        # Load face detector (Haar Cascade)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # For smoothing predictions over multiple frames
        self.prediction_history = deque(maxlen=10)
        
        # FPS calculation
        self.fps_history = deque(maxlen=30)
        self.last_time = time.time()
        
        # Recognition cooldown (to avoid too frequent predictions)
        self.last_recognition_time = 0
        self.recognition_cooldown = 0.5  # seconds
        
        # Cache for current prediction
        self.current_prediction = None
        self.prediction_confidence = 0
        
    def detect_faces(self, frame):
        """
        Detect faces in a frame using Haar Cascade.
        
        Args:
            frame: BGR image from webcam
            
        Returns:
            List of (x, y, w, h) tuples for detected faces
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        return faces
    
    def preprocess_face(self, frame, face_coords):
        """
        Extract and preprocess a face region for the model.
        
        Args:
            frame: BGR image from webcam
            face_coords: (x, y, w, h) tuple
            
        Returns:
            Preprocessed face image array
        """
        x, y, w, h = face_coords
        
        # Add some padding around the face
        padding = int(0.2 * w)
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(frame.shape[1], x + w + padding)
        y2 = min(frame.shape[0], y + h + padding)
        
        # Extract face region
        face_img = frame[y1:y2, x1:x2]
        
        # Convert BGR to RGB
        face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        
        # Resize to model input size
        face_img = cv2.resize(face_img, self.recognizer.img_size)
        
        # Normalize
        face_img = face_img.astype(np.float32) / 255.0
        
        return face_img
    
    def recognize_face(self, face_img):
        """
        Recognize a face using the embedding model.
        
        Args:
            face_img: Preprocessed face image array
            
        Returns:
            Dictionary with recognition results
        """
        # Get embedding
        img_batch = np.expand_dims(face_img, axis=0)
        query_embedding = self.recognizer.model.predict(img_batch, verbose=0)[0]
        
        if not self.recognizer.embeddings_db:
            return {"name": "No Database", "confidence": 0, "is_recognized": False}
        
        # Compare with database
        best_match = None
        best_score = -float('inf') if self.use_cosine else float('inf')
        
        for person_name, embeddings in self.recognizer.embeddings_db.items():
            for emb in embeddings:
                if self.use_cosine:
                    score = self.recognizer.compute_cosine_similarity(query_embedding, emb)
                    if score > best_score:
                        best_score = score
                        best_match = person_name
                else:
                    score = self.recognizer.compute_distance(query_embedding, emb)
                    if score < best_score:
                        best_score = score
                        best_match = person_name
        
        # Determine if recognized
        if self.use_cosine:
            is_recognized = best_score >= self.threshold
            confidence = best_score
        else:
            is_recognized = best_score <= self.threshold
            confidence = max(0, 1 - best_score / (2 * self.threshold))
        
        return {
            "name": best_match if is_recognized else "Unknown",
            "confidence": confidence,
            "is_recognized": is_recognized,
            "raw_score": best_score
        }
    
    def smooth_prediction(self, prediction):
        """
        Smooth predictions over multiple frames.
        
        Args:
            prediction: Current frame prediction
            
        Returns:
            Smoothed prediction
        """
        self.prediction_history.append(prediction)
        
        if len(self.prediction_history) < 3:
            return prediction
        
        # Count occurrences of each name
        name_counts = {}
        confidence_sums = {}
        
        for pred in self.prediction_history:
            name = pred['name']
            conf = pred['confidence']
            
            if name not in name_counts:
                name_counts[name] = 0
                confidence_sums[name] = 0
            
            name_counts[name] += 1
            confidence_sums[name] += conf
        
        # Get most common name
        most_common = max(name_counts.items(), key=lambda x: x[1])
        name = most_common[0]
        avg_confidence = confidence_sums[name] / name_counts[name]
        
        return {
            "name": name,
            "confidence": avg_confidence,
            "is_recognized": name != "Unknown",
            "raw_score": prediction['raw_score']
        }
    
    def draw_results(self, frame, faces, predictions):
        """
        Draw bounding boxes and labels on the frame.
        
        Args:
            frame: BGR image from webcam
            faces: List of face coordinates
            predictions: List of prediction results
        """
        for (x, y, w, h), pred in zip(faces, predictions):
            # Choose color based on recognition
            if pred['is_recognized']:
                color = (0, 255, 0)  # Green for recognized
            else:
                color = (0, 0, 255)  # Red for unknown
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Prepare label
            name = pred['name']
            if self.use_cosine:
                conf_text = f"{pred['confidence']:.2f}"
            else:
                conf_text = f"{pred['raw_score']:.2f}"
            
            label = f"{name} ({conf_text})"
            
            # Draw label background
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x, y - 25), (x + label_size[0], y), color, -1)
            
            # Draw label text
            cv2.putText(frame, label, (x, y - 7), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.6, (255, 255, 255), 2)
        
        return frame
    
    def draw_info(self, frame, fps, num_faces):
        """
        Draw information overlay on the frame.
        
        Args:
            frame: BGR image
            fps: Current FPS
            num_faces: Number of detected faces
        """
        # Draw semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (250, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        # Draw info text
        cv2.putText(frame, f"FPS: {fps:.1f}", (20, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Faces: {num_faces}", (20, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Threshold: {self.threshold}", (20, 85), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw controls info at bottom
        h = frame.shape[0]
        cv2.putText(frame, "Press 'q' to quit | '+'/'-' adjust threshold", 
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return frame
    
    def calculate_fps(self):
        """Calculate current FPS."""
        current_time = time.time()
        fps = 1.0 / (current_time - self.last_time + 1e-8)
        self.last_time = current_time
        self.fps_history.append(fps)
        return np.mean(self.fps_history)
    
    def run(self, camera_id=0, window_name="Face Recognition", show_all_faces=True):
        """
        Run the real-time face recognition.
        
        Args:
            camera_id: Camera device ID (default: 0)
            window_name: Name of the display window
            show_all_faces: Whether to recognize all faces or just the largest one
        """
        # Build database first
        print("\nBuilding face database...")
        self.recognizer.build_database()
        
        if not self.recognizer.embeddings_db:
            print("ERROR: No faces in database. Add images to the Detected Faces folder.")
            return
        
        print(f"\nDatabase contains {len(self.recognizer.embeddings_db)} people")
        print("\nStarting webcam...")
        
        # Open webcam
        cap = cv2.VideoCapture(camera_id)
        
        if not cap.isOpened():
            print(f"ERROR: Could not open camera {camera_id}")
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print("\n" + "=" * 50)
        print("Real-time Face Recognition Started!")
        print("=" * 50)
        print("\nControls:")
        print("  'q' - Quit")
        print("  '+' - Increase threshold")
        print("  '-' - Decrease threshold")
        print("  's' - Save current frame")
        print("  'r' - Rebuild database")
        print("=" * 50 + "\n")
        
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("ERROR: Could not read frame from camera")
                    break
                
                frame_count += 1
                
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Detect faces
                faces = self.detect_faces(frame)
                
                predictions = []
                
                # Process each face
                current_time = time.time()
                
                for i, (x, y, w, h) in enumerate(faces):
                    # If not showing all faces, only process the largest
                    if not show_all_faces and i > 0:
                        break
                    
                    # Check cooldown
                    if current_time - self.last_recognition_time >= self.recognition_cooldown:
                        # Preprocess face
                        face_img = self.preprocess_face(frame, (x, y, w, h))
                        
                        # Recognize
                        prediction = self.recognize_face(face_img)
                        
                        # Smooth prediction
                        prediction = self.smooth_prediction(prediction)
                        
                        self.current_prediction = prediction
                        self.last_recognition_time = current_time
                    else:
                        # Use cached prediction
                        prediction = self.current_prediction or {
                            "name": "Processing...",
                            "confidence": 0,
                            "is_recognized": False,
                            "raw_score": 0
                        }
                    
                    predictions.append(prediction)
                
                # Draw results
                frame = self.draw_results(frame, faces, predictions)
                
                # Calculate and draw FPS
                fps = self.calculate_fps()
                frame = self.draw_info(frame, fps, len(faces))
                
                # Display
                cv2.imshow(window_name, frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\nQuitting...")
                    break
                elif key == ord('+') or key == ord('='):
                    if self.use_cosine:
                        self.threshold = min(1.0, self.threshold + 0.05)
                    else:
                        self.threshold = self.threshold + 0.5
                    print(f"Threshold: {self.threshold:.2f}")
                elif key == ord('-') or key == ord('_'):
                    if self.use_cosine:
                        self.threshold = max(0.0, self.threshold - 0.05)
                    else:
                        self.threshold = max(0.1, self.threshold - 0.5)
                    print(f"Threshold: {self.threshold:.2f}")
                elif key == ord('s'):
                    # Save current frame
                    filename = f"capture_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"Saved: {filename}")
                elif key == ord('r'):
                    # Rebuild database
                    print("\nRebuilding database...")
                    self.recognizer.build_database()
                    self.prediction_history.clear()
                    print("Database rebuilt!")
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("Camera released. Goodbye!")


def main():
    parser = argparse.ArgumentParser(description='Real-time Face Recognition')
    parser.add_argument('--model', type=str, default='face_embeddings_model.keras',
                        help='Path to trained model')
    parser.add_argument('--database_dir', type=str, default='Detected Faces',
                        help='Directory containing face database images')
    parser.add_argument('--threshold', type=float, default=0.9,
                        help='Recognition threshold')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera device ID')
    parser.add_argument('--use_euclidean', action='store_true',
                        help='Use Euclidean distance instead of cosine similarity')
    parser.add_argument('--load_db', type=str, default=None,
                        help='Path to pre-computed embeddings database')
    
    args = parser.parse_args()
    
    # Get base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, args.model) if not os.path.isabs(args.model) else args.model
    database_dir = os.path.join(base_dir, args.database_dir) if not os.path.isabs(args.database_dir) else args.database_dir
    
    # Check if model exists
    if not os.path.exists(model_path):
        print(f"ERROR: Model not found at {model_path}")
        print("Please train a model first using: python train_face_recognition.py --mode train")
        return 1
    
    # Check if database directory exists
    if not os.path.exists(database_dir):
        print(f"ERROR: Database directory not found at {database_dir}")
        return 1
    
    # Initialize and run
    use_cosine = not args.use_euclidean
    
    realtime = RealtimeFaceRecognizer(
        model_path=model_path,
        database_dir=database_dir,
        threshold=args.threshold,
        use_cosine=use_cosine
    )
    
    # Load pre-computed database if specified
    if args.load_db and os.path.exists(args.load_db):
        realtime.recognizer.load_database(args.load_db)
    
    # Run real-time recognition
    realtime.run(camera_id=args.camera)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
