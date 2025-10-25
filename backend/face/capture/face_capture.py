# Face Capture Module
# This module captures exactly 5 photos of a person for registration

import cv2
import os
import time

class FaceCapture:
    def __init__(self):
        """Initialize the face capture system"""
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.max_photos = 5
        
    def capture_user_photos(self, user_name, save_path="../../../dataset/face"):
        """
        Capture exactly 5 photos for user registration
        
        Args:
            user_name (str): Name of the user
            save_path (str): Base path to save captured faces
        """
        # Create user directory
        user_folder = os.path.join(save_path, user_name)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
            print(f"Created directory for user: {user_name}")
        else:
            print(f"Directory already exists for user: {user_name}")
            
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return False
            
        print(f"\n=== Face Registration for {user_name} ===")
        print("Position your face in the camera view")
        print("The system will automatically capture 5 photos")
        print("Press 'q' to quit early\n")
        
        captured_count = 0
        
        while captured_count < self.max_photos:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame")
                break
                
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            # Draw rectangles around faces and status
            display_frame = frame.copy()
            
            if len(faces) > 0:
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(display_frame, "Face Detected - Ready to Capture", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                cv2.putText(display_frame, "No Face Detected", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # Show progress
            progress_text = f"Photos captured: {captured_count}/{self.max_photos}"
            cv2.putText(display_frame, progress_text, (50, display_frame.shape[0] - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow(f'Face Registration - {user_name}', display_frame)
            
            # Auto-capture when face is detected
            if len(faces) > 0:
                # Use the first detected face
                x, y, w, h = faces[0]
                
                # Extract and save face
                face_img = frame[y:y+h, x:x+w]
                
                # Generate filename: face_001, face_002, etc.
                filename = f"face_{captured_count + 1:03d}.jpg"
                filepath = os.path.join(user_folder, filename)
                
                # Save the face image
                cv2.imwrite(filepath, face_img)
                captured_count += 1
                
                print(f"✓ Captured photo {captured_count}/{self.max_photos}: {filename}")
                
                # Wait 2 seconds before next capture
                if captured_count < self.max_photos:
                    print("  Next photo in 2 seconds...")
                    time.sleep(2)
            
            # Check for quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nCapture session cancelled by user")
                break
        
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        
        if captured_count == self.max_photos:
            print(f"\n✅ Registration complete for {user_name}!")
            print(f"   {captured_count} photos saved in: {user_folder}")
            return True
        else:
            print(f"\n⚠️  Registration incomplete. Only {captured_count} photos captured.")
            return False

def main():
    """Main function to run face capture"""
    face_capture = FaceCapture()
    
    # Get user name
    print("=== Face Registration System ===")
    user_name = input("Enter your name: ").strip()
    
    if not user_name:
        print("Error: Please enter a valid name")
        return
    
    # Start capture session
    success = face_capture.capture_user_photos(user_name)
    
    if success:
        print(f"\n🎉 Welcome {user_name}! Your face data has been registered successfully.")
    else:
        print(f"\n❌ Registration failed for {user_name}. Please try again.")

if __name__ == "__main__":
    main()
