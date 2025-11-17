#!/usr/bin/env python3
"""
Test Face Matching Webcam
Simple test script to verify webcam functionality in face matching
"""

import sys
import os

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from face.match.face_match import DatabaseFaceMatcher

def test_face_matching():
    """Test the face matching webcam functionality"""
    print("=== Face Matching Webcam Test ===")
    
    try:
        # Initialize the face matcher
        print("Initializing face matcher...")
        matcher = DatabaseFaceMatcher()
        
        # Test webcam face matching
        print("Starting webcam face matching (15 seconds)...")
        print("Press 'q' at any time to quit early")
        
        result = matcher.match_face_from_webcam(duration_seconds=15)
        
        print("\n=== Results ===")
        print(f"Success: {result['success']}")
        
        if result['success']:
            print(f"Matched User: {result['matched_user']}")
            print(f"Confidence: {result['confidence']:.3f}")
            print(f"Message: {result['message']}")
        else:
            print(f"Error: {result['error']}")
            if 'best_confidence' in result:
                print(f"Best Confidence: {result['best_confidence']:.3f}")
            if 'message' in result:
                print(f"Message: {result['message']}")
                
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_face_matching()
