#!/usr/bin/env python3
"""
Webcam Test Script for Biometric System
Tests camera availability and basic functionality
"""

import cv2
import sys
import time

def test_webcam():
    """Test webcam availability and functionality"""
    print("=== Webcam Test ===")
    
    # Test different camera indices
    camera_indices = [0, 1, 2]
    working_cameras = []
    
    for index in camera_indices:
        print(f"\nTesting camera index {index}...")
        
        try:
            cap = cv2.VideoCapture(index)
            
            # Set properties for better compatibility
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if cap.isOpened():
                # Try to read a frame
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"✓ Camera {index} is working!")
                    print(f"  Resolution: {frame.shape[1]}x{frame.shape[0]}")
                    working_cameras.append(index)
                else:
                    print(f"✗ Camera {index} opened but no frame received")
            else:
                print(f"✗ Camera {index} failed to open")
            
            cap.release()
            
        except Exception as e:
            print(f"✗ Camera {index} error: {e}")
    
    if not working_cameras:
        print("\n❌ No working cameras found!")
        print("\nTroubleshooting steps:")
        print("1. Check if camera is connected properly")
        print("2. Close other applications using the camera")
        print("3. Check camera permissions in Windows settings")
        print("4. Try running as administrator")
        return False
    else:
        print(f"\n✓ Found {len(working_cameras)} working camera(s): {working_cameras}")
        
        # Test the first working camera with live preview
        test_index = working_cameras[0]
        print(f"\nTesting live preview with camera {test_index}...")
        
        try:
            cap = cv2.VideoCapture(test_index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            if cap.isOpened():
                print("Press 'q' to quit the test preview")
                
                frame_count = 0
                start_time = time.time()
                
                while True:
                    ret, frame = cap.read()
                    
                    if not ret:
                        print("Failed to read frame")
                        break
                    
                    frame_count += 1
                    
                    # Add status text
                    cv2.putText(frame, f"Camera Test - Frame {frame_count}", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, "Press 'q' to quit", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Calculate FPS
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        fps = frame_count / elapsed
                        cv2.putText(frame, f"FPS: {fps:.1f}", 
                                   (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    
                    cv2.imshow('Webcam Test', frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                        
                    # Auto-quit after 10 seconds
                    if elapsed > 10:
                        print("Auto-quit after 10 seconds")
                        break
                
                cap.release()
                cv2.destroyAllWindows()
                print("✓ Camera test completed successfully!")
                return True
            else:
                print("Failed to open camera for live test")
                return False
                
        except Exception as e:
            print(f"Live test error: {e}")
            return False

def test_opencv_installation():
    """Test OpenCV installation"""
    print("\n=== OpenCV Installation Test ===")
    
    try:
        print(f"OpenCV version: {cv2.__version__}")
        
        # Test video codec support
        fourcc_codes = ['XVID', 'MJPG', 'YUYV', 'H264']
        for codec in fourcc_codes:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                print(f"✓ Codec {codec} supported")
            except:
                print(f"✗ Codec {codec} not supported")
        
        return True
        
    except Exception as e:
        print(f"OpenCV test failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting comprehensive webcam test...\n")
    
    # Test OpenCV installation
    opencv_ok = test_opencv_installation()
    
    if opencv_ok:
        # Test webcam
        webcam_ok = test_webcam()
        
        if webcam_ok:
            print("\n🎉 All tests passed! Webcam should work in face matching.")
        else:
            print("\n❌ Webcam test failed. Check the troubleshooting steps above.")
    else:
        print("\n❌ OpenCV installation issue detected.")
