#!/usr/bin/env python3
"""
Steganography Module for Biometric Authentication System
Embeds SHA-256 fingerprint keys into face images using LSB (Least Significant Bit) technique
"""

import cv2
import numpy as np
from PIL import Image
import io
import base64

class BiometricSteganography:
    """Class for embedding and extracting biometric keys in/from images"""
    
    def __init__(self):
        self.delimiter = "|||END_OF_KEY|||"  # Delimiter to mark end of hidden data
    
    def string_to_binary(self, text):
        """Convert string to binary representation"""
        return ''.join(format(ord(char), '08b') for char in text)
    
    def binary_to_string(self, binary):
        """Convert binary representation back to string"""
        chars = [binary[i:i+8] for i in range(0, len(binary), 8)]
        return ''.join(chr(int(char, 2)) for char in chars if len(char) == 8)
    
    def embed_key_in_image(self, image_data, fingerprint_key):
        """
        Embed fingerprint key into image using LSB steganography
        
        Args:
            image_data: Binary image data (JPEG/PNG)
            fingerprint_key: SHA-256 key (64-character hex string)
            
        Returns:
            tuple: (success, modified_image_data, message)
        """
        try:
            # Convert binary data to PIL Image
            image_buffer = io.BytesIO(image_data)
            image = Image.open(image_buffer)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            img_array = np.array(image)
            height, width, channels = img_array.shape
            
            # Prepare data to hide: key + delimiter
            data_to_hide = fingerprint_key + self.delimiter
            binary_data = self.string_to_binary(data_to_hide)
            
            # Check if image can hold the data
            max_capacity = height * width * channels
            if len(binary_data) > max_capacity:
                return False, None, "Image too small to hold the fingerprint key"
            
            # Flatten image array
            flat_img = img_array.flatten()
            
            # Embed data using LSB
            for i, bit in enumerate(binary_data):
                # Modify the least significant bit
                flat_img[i] = (flat_img[i] & 0xFE) | int(bit)
            
            # Reshape back to original dimensions
            modified_img = flat_img.reshape(height, width, channels)
            
            # Convert back to PIL Image
            result_image = Image.fromarray(modified_img.astype(np.uint8))
            
            # Save to bytes
            output_buffer = io.BytesIO()
            result_image.save(output_buffer, format='PNG', quality=95)
            modified_image_data = output_buffer.getvalue()
            
            print(f"✅ Successfully embedded {len(fingerprint_key)} character key into image")
            print(f"   - Original image size: {len(image_data)} bytes")
            print(f"   - Modified image size: {len(modified_image_data)} bytes")
            print(f"   - Key preview: {fingerprint_key[:16]}...{fingerprint_key[-16:]}")
            
            return True, modified_image_data, "Fingerprint key successfully embedded in image"
            
        except Exception as e:
            print(f"❌ Error embedding key in image: {e}")
            return False, None, f"Steganography error: {str(e)}"
    
    def extract_key_from_image(self, image_data):
        """
        Extract fingerprint key from image using LSB steganography
        
        Args:
            image_data: Binary image data containing hidden key
            
        Returns:
            tuple: (success, extracted_key, message)
        """
        try:
            # Convert binary data to PIL Image
            image_buffer = io.BytesIO(image_data)
            image = Image.open(image_buffer)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array and flatten
            img_array = np.array(image)
            flat_img = img_array.flatten()
            
            # Extract binary data from LSB
            binary_data = ''
            
            # Read enough bits to find the delimiter
            max_bits = len(flat_img)
            delimiter_binary = self.string_to_binary(self.delimiter)
            
            for i in range(max_bits):
                binary_data += str(flat_img[i] & 1)  # Extract LSB
                
                # Check for delimiter every 8 bits (after each potential character)
                if len(binary_data) % 8 == 0 and len(binary_data) >= len(delimiter_binary):
                    try:
                        # Convert current binary to string
                        current_text = self.binary_to_string(binary_data)
                        
                        # Check if delimiter is present
                        if self.delimiter in current_text:
                            # Extract the key part (before delimiter)
                            parts = current_text.split(self.delimiter)
                            if len(parts) > 1:
                                fingerprint_key = parts[0]
                                
                                # Validate key format (64 character hex)
                                if len(fingerprint_key) == 64 and all(c in '0123456789abcdefABCDEF' for c in fingerprint_key):
                                    print(f"✅ Successfully extracted fingerprint key from image")
                                    print(f"   - Key preview: {fingerprint_key[:16]}...{fingerprint_key[-16:]}")
                                    return True, fingerprint_key.lower(), "Fingerprint key successfully extracted"
                    except (UnicodeDecodeError, ValueError):
                        # Continue if we can't decode properly yet
                        continue
            
            return False, None, "No valid fingerprint key found in image"
            
        except Exception as e:
            print(f"❌ Error extracting key from image: {e}")
            return False, None, f"Extraction error: {str(e)}"
    
    def verify_key_in_image(self, image_data, expected_key):
        """
        Verify that a specific key is embedded in the image
        
        Args:
            image_data: Binary image data
            expected_key: Expected fingerprint key
            
        Returns:
            bool: True if key matches, False otherwise
        """
        success, extracted_key, message = self.extract_key_from_image(image_data)
        
        if success and extracted_key == expected_key:
            print(f"✅ Key verification successful - keys match")
            return True
        else:
            print(f"❌ Key verification failed - keys do not match")
            return False

def test_steganography():
    """Test function for steganography operations"""
    print("=== Biometric Steganography Test ===")
    
    # Create test data (proper 64-character SHA-256 key)
    test_key = "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd"
    
    # Create a simple test image
    test_image = Image.new('RGB', (200, 200), color='blue')
    test_buffer = io.BytesIO()
    test_image.save(test_buffer, format='PNG')
    test_image_data = test_buffer.getvalue()
    
    # Initialize steganography
    steg = BiometricSteganography()
    
    # Test embedding
    print("\n1. Testing key embedding...")
    print(f"Test key: {test_key} (length: {len(test_key)})")
    success, modified_data, message = steg.embed_key_in_image(test_image_data, test_key)
    print(f"Embedding result: {message}")
    
    if success:
        # Test extraction
        print("\n2. Testing key extraction...")
        success2, extracted_key, message2 = steg.extract_key_from_image(modified_data)
        print(f"Extraction result: {message2}")
        
        if success2:
            print(f"Extracted key: {extracted_key} (length: {len(extracted_key)})")
            print(f"Keys match: {test_key.lower() == extracted_key.lower()}")
            
            # Test verification
            print("\n3. Testing key verification...")
            verification_result = steg.verify_key_in_image(modified_data, test_key)
            print(f"Verification result: {'PASSED' if verification_result else 'FAILED'}")
        else:
            print("❌ Extraction failed, cannot test verification")
    else:
        print("❌ Embedding failed, cannot proceed with tests")

if __name__ == "__main__":
    test_steganography()
