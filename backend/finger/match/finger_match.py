#!/usr/bin/env python3
"""
R307 Real-time Fingerprint Matcher for User Authentication
Loads user's fingerprint template and matches it with live fingerprint capture
The live template is not stored anywhere - only used for matching

Hardware: R307 Fingerprint Sensor connected to COM3
Author: Created for user authentication via fingerprint matching
"""

import serial
import time
import struct
import os
from datetime import datetime

class R307FingerMatcher:
    """Interface for R307 fingerprint sensor real-time matching"""
    
    # Command codes
    CMD_GET_IMAGE = 0x01
    CMD_IMG_2_TZ = 0x02
    CMD_MATCH = 0x03
    CMD_UP_CHAR = 0x08
    CMD_DOWN_CHAR = 0x09
    
    # Response codes
    FINGERPRINT_OK = 0x00
    FINGERPRINT_PACKETRECIEVEERR = 0x01
    FINGERPRINT_NOFINGER = 0x02
    FINGERPRINT_IMAGEFAIL = 0x03
    FINGERPRINT_IMAGEMESS = 0x06
    FINGERPRINT_FEATUREFAIL = 0x07
    FINGERPRINT_NOMATCH = 0x08
    FINGERPRINT_INVALIDIMAGE = 0x15
    
    # Package identifiers
    FINGERPRINT_STARTCODE = 0xEF01
    FINGERPRINT_COMMANDPACKET = 0x01
    FINGERPRINT_DATAPACKET = 0x02
    FINGERPRINT_ACKPACKET = 0x07
    FINGERPRINT_ENDDATAPACKET = 0x08
    
    def __init__(self, port='COM3', baud_rate=57600, address=0xFFFFFFFF):
        """Initialize connection to R307 sensor"""
        self.port = port
        self.baud_rate = baud_rate
        self.address = address
        self.serial_conn = None
        
    def connect(self):
        """Establish serial connection to sensor"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2
            )
            print(f"✅ Connected to R307 sensor on {self.port}")
            return True
        except serial.SerialException as e:
            print(f"❌ Failed to connect to sensor: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Disconnected from sensor")
    
    def _write_packet(self, packet_type, data):
        """Write packet to sensor with proper header and checksum"""
        packet = struct.pack('>H', self.FINGERPRINT_STARTCODE)
        packet += struct.pack('>I', self.address)
        packet += struct.pack('>B', packet_type)
        packet += struct.pack('>H', len(data) + 2)
        packet += data
        
        # Calculate checksum
        checksum = packet_type + len(data) + 2 + sum(data)
        packet += struct.pack('>H', checksum)
        
        self.serial_conn.write(packet)
        
    def _read_packet(self):
        """Read response packet from sensor"""
        # Read header
        header = self.serial_conn.read(2)
        if len(header) != 2:
            return None, None
            
        start_code = struct.unpack('>H', header)[0]
        if start_code != self.FINGERPRINT_STARTCODE:
            return None, None
        
        # Read address
        addr_data = self.serial_conn.read(4)
        if len(addr_data) != 4:
            return None, None
        
        # Read packet identifier
        pid_data = self.serial_conn.read(1)
        if len(pid_data) != 1:
            return None, None
        packet_type = struct.unpack('>B', pid_data)[0]
        
        # Read length
        len_data = self.serial_conn.read(2)
        if len(len_data) != 2:
            return None, None
        packet_len = struct.unpack('>H', len_data)[0]
        
        # Read data and checksum
        data_and_checksum = self.serial_conn.read(packet_len)
        if len(data_and_checksum) != packet_len:
            return None, None
        
        data = data_and_checksum[:-2]
        return packet_type, data
    
    def load_template_file(self, filename):
        """Load template data from .bin file"""
        try:
            with open(filename, 'rb') as f:
                template_data = f.read()
            print(f"✅ Loaded template: {filename} ({len(template_data)} bytes)")
            return template_data
        except FileNotFoundError:
            print(f"❌ Template file not found: {filename}")
            return None
        except Exception as e:
            print(f"❌ Error loading template file {filename}: {e}")
            return None
    
    def download_template(self, template_data, buffer_id=1):
        """Download template data to sensor buffer"""
        print(f"📥 Downloading template to buffer {buffer_id}...")
        
        # Send download command
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_DOWN_CHAR, buffer_id]))
        
        # Read ACK packet
        packet_type, data = self._read_packet()
        if packet_type != self.FINGERPRINT_ACKPACKET or len(data) == 0 or data[0] != self.FINGERPRINT_OK:
            print("❌ Failed to initiate template download")
            return False
        
        # Send template data in packets
        chunk_size = 128  # Typical data packet size
        data_sent = 0
        
        while data_sent < len(template_data):
            chunk_end = min(data_sent + chunk_size, len(template_data))
            chunk = template_data[data_sent:chunk_end]
            
            if chunk_end == len(template_data):
                # Last packet - use end data packet type
                self._write_packet(self.FINGERPRINT_ENDDATAPACKET, chunk)
            else:
                # Regular data packet
                self._write_packet(self.FINGERPRINT_DATAPACKET, chunk)
            
            data_sent = chunk_end
        
        print("✅ Template downloaded successfully")
        return True
    
    def get_image(self):
        """Capture fingerprint image from sensor"""
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_GET_IMAGE]))
        
        packet_type, data = self._read_packet()
        if packet_type == self.FINGERPRINT_ACKPACKET and len(data) > 0:
            response_code = data[0]
            if response_code == self.FINGERPRINT_OK:
                return True
            elif response_code == self.FINGERPRINT_NOFINGER:
                return False
            elif response_code == self.FINGERPRINT_IMAGEFAIL:
                return False
            else:
                return False
        return False
    
    def image_2_template(self, buffer_id=2):
        """Convert captured image to template in specified buffer"""
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_IMG_2_TZ, buffer_id]))
        
        packet_type, data = self._read_packet()
        if packet_type == self.FINGERPRINT_ACKPACKET and len(data) > 0:
            response_code = data[0]
            if response_code == self.FINGERPRINT_OK:
                return True
            elif response_code == self.FINGERPRINT_IMAGEMESS:
                return False
            elif response_code == self.FINGERPRINT_FEATUREFAIL:
                return False
            else:
                return False
        return False
    
    def match_templates(self):
        """Match templates in buffer 1 and buffer 2"""
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_MATCH]))
        
        packet_type, data = self._read_packet()
        if packet_type == self.FINGERPRINT_ACKPACKET and len(data) >= 3:
            response_code = data[0]
            if response_code == self.FINGERPRINT_OK:
                # Extract confidence score
                confidence = struct.unpack('>H', data[1:3])[0]
                return True, confidence
            elif response_code == self.FINGERPRINT_NOMATCH:
                return False, 0
            else:
                return False, 0
        return False, 0
    
    def capture_and_get_template(self):
        """Capture fingerprint and return template data for SHA-256 key generation"""
        # Connect to sensor
        if not self.connect():
            return False, None, "Failed to connect to fingerprint sensor"
        
        try:
            print("👆 Place your finger on the sensor for template capture...")
            
            # Try to capture fingerprint (with retries)
            max_attempts = 5
            for attempt in range(max_attempts):
                print(f"Template capture attempt {attempt + 1}/{max_attempts}")
                
                # Capture fingerprint image
                if not self.get_image():
                    print("❌ No finger detected, please place finger on sensor")
                    time.sleep(1)
                    continue
                
                # Convert image to template in buffer 1
                if not self.image_2_template(buffer_id=1):
                    print("❌ Failed to generate template from fingerprint")
                    time.sleep(1)
                    continue
                
                # Upload template from buffer 1 to get template data
                print("📤 Reading template data from sensor...")
                
                # Send upload command to get template data from buffer 1
                cmd = struct.pack('>BH', self.CMD_UP_CHAR, 1)  # Buffer 1
                self._write_packet(self.FINGERPRINT_COMMANDPACKET, cmd)
                
                # Read acknowledgment packet first
                ack_packet = self._read_packet()
                if ack_packet and len(ack_packet) > 0 and ack_packet[0] == self.FINGERPRINT_OK:
                    print("✅ Sensor ready to send template data")
                    
                    # Now read the actual template data packets
                    template_data = b''
                    packet_count = 0
                    expected_size = 512  # Standard R307 template size
                    
                    while packet_count < 20 and len(template_data) < expected_size:  # Safety limit
                        try:
                            # Read data packet
                            data_packet = self._read_packet()
                            if data_packet is None:
                                print(f"No more data packets received after {packet_count} packets")
                                break
                                
                            # Add the packet data
                            if isinstance(data_packet, bytes) and len(data_packet) > 0:
                                template_data += data_packet
                                packet_count += 1
                                print(f"Packet {packet_count}: {len(data_packet)} bytes (total: {len(template_data)})")
                                
                                # Check if we have complete template
                                if len(template_data) >= expected_size:
                                    print("Template data complete")
                                    break
                            else:
                                print(f"Invalid packet data: {type(data_packet)}")
                                break
                                
                        except Exception as e:
                            print(f"Error reading packet {packet_count}: {e}")
                            break
                    
                    # Validate and normalize template data
                    if len(template_data) >= 200:  # Minimum reasonable template size
                        # Ensure consistent size for SHA-256 key generation
                        if len(template_data) > expected_size:
                            template_data = template_data[:expected_size]
                        elif len(template_data) < expected_size:
                            # Pad with zeros to ensure consistent size
                            template_data += b'\x00' * (expected_size - len(template_data))
                            
                        print(f"✅ Template captured successfully ({len(template_data)} bytes)")
                        print(f"Template preview: {template_data[:20].hex()}...")
                        return True, template_data, "Template captured successfully"
                    else:
                        print(f"❌ Template data too small: {len(template_data)} bytes")
                        continue
                else:
                    error_code = ack_packet[0] if ack_packet and len(ack_packet) > 0 else "unknown"
                    print(f"❌ Template upload failed with error code: {error_code}")
                    continue
            
            return False, None, f"Failed to capture template after {max_attempts} attempts"
            
        except Exception as e:
            print(f"❌ Template capture error: {e}")
            return False, None, f"Template capture error: {str(e)}"
        finally:
            self.disconnect()
    
    def authenticate_user_with_template(self, username, template_data):
        """Authenticate user by matching live fingerprint with provided template data"""
        # Connect to sensor
        if not self.connect():
            return False, 0, "Failed to connect to fingerprint sensor"
        
        try:
            # Download stored template to buffer 1
            if not self.download_template(template_data, buffer_id=1):
                return False, 0, "Failed to download template to sensor"
            
            print("👆 Place your finger on the sensor for authentication...")
            
            # Try to capture and match fingerprint (with retries)
            max_attempts = 5
            for attempt in range(max_attempts):
                print(f"Attempt {attempt + 1}/{max_attempts}")
                
                # Capture live fingerprint
                if not self.get_image():
                    print("❌ No finger detected, please place finger on sensor")
                    time.sleep(1)
                    continue
                
                # Convert live image to template in buffer 2 (temporary, not stored)
                if not self.image_2_template(buffer_id=2):
                    print("❌ Failed to generate template from live image")
                    time.sleep(1)
                    continue
                
                # Perform matching inside the sensor
                match_result, confidence = self.match_templates()
                
                if match_result:
                    return True, confidence, f"Authentication successful! Confidence: {confidence}"
                else:
                    print(f"❌ No match (attempt {attempt + 1})")
                    time.sleep(1)
            
            return False, 0, "Authentication failed after multiple attempts"
            
        except Exception as e:
            return False, 0, f"Error during authentication: {str(e)}"
        finally:
            self.disconnect()

def get_registered_users(dataset_path="../../../dataset"):
    """Get list of registered users from dataset folder"""
    try:
        if not os.path.exists(dataset_path):
            return []
        
        users = []
        for item in os.listdir(dataset_path):
            user_path = os.path.join(dataset_path, item)
            if os.path.isdir(user_path):
                # Check if user has fingerprint file
                fingerprint_file = os.path.join(user_path, "fingerprint.bin")
                if os.path.exists(fingerprint_file):
                    users.append(item)
        
        return users
    except Exception as e:
        print(f"Error getting registered users: {e}")
        return []

def main():
    """Test function for fingerprint authentication"""
    print("R307 Fingerprint Authentication System")
    print("=====================================")
    
    # Get list of registered users
    users = get_registered_users()
    
    if not users:
        print("No registered users found with fingerprint data.")
        return
    
    print("Registered users:")
    for i, user in enumerate(users, 1):
        print(f"{i}. {user}")
    
    try:
        choice = int(input("\nSelect user number: ")) - 1
        if choice < 0 or choice >= len(users):
            print("Invalid selection")
            return
        
        selected_user = users[choice]
        print(f"\nAuthenticating user: {selected_user}")
        
        # Create matcher instance
        matcher = R307FingerMatcher()
        
        # Perform authentication
        success, confidence, message = matcher.authenticate_user(selected_user)
        
        print(f"\n{message}")
        
        if success:
            print(f"🎉 Welcome, {selected_user}!")
        else:
            print(f"🚫 Access denied for {selected_user}")
            
    except ValueError:
        print("Please enter a valid number")
    except KeyboardInterrupt:
        print("\nAuthentication cancelled")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
