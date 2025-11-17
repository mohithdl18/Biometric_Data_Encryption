#!/usr/bin/env python3
"""
R307 Real-time Fingerprint Matcher
Loads finger1.bin template and matches it with live fingerprint capture
The live template is not stored anywhere - only used for matching

Hardware: R307 Fingerprint Sensor connected to COM3
Author: Created for real-time fingerprint matching
"""

import serial
import time
import struct
import os
from datetime import datetime

class R307RealTimeMatcher:
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
            print(f"Connected to R307 sensor on {self.port}")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to sensor: {e}")
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
            return template_data
        except FileNotFoundError:
            print(f"Template file not found: {filename}")
            return None
        except Exception as e:
            print(f"Error loading template file {filename}: {e}")
            return None
    
    def download_template(self, template_data, buffer_id=1):
        """Download template data to sensor buffer"""
        # Send download command
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_DOWN_CHAR, buffer_id]))
        
        # Read ACK packet
        packet_type, data = self._read_packet()
        if packet_type != self.FINGERPRINT_ACKPACKET or len(data) == 0 or data[0] != self.FINGERPRINT_OK:
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
    
    def match_live_with_stored(self, template_file):
        """Match live fingerprint capture with stored template file"""
        # Load stored template file
        template_data = self.load_template_file(template_file)
        if not template_data:
            return False, 0
        
        # Download stored template to buffer 1
        if not self.download_template(template_data, buffer_id=1):
            return False, 0
        
        # Capture live fingerprint
        if not self.get_image():
            return False, 0
        
        # Convert live image to template in buffer 2 (temporary, not stored)
        if not self.image_2_template(buffer_id=2):
            return False, 0
        
        # Perform matching inside the sensor
        return self.match_templates()

def main():
    """Main function to perform real-time fingerprint matching"""
    print("R307 Real-time Fingerprint Matcher")
    print("==================================")
    
    # Check if finger1.bin exists
    if not os.path.exists('finger1.bin'):
        print("✗ Missing: finger1.bin")
        print("Please run scan.py first to create finger1.bin template.")
        return
    
    # Create matcher instance
    matcher = R307RealTimeMatcher(port='COM3')
    
    try:
        # Connect to sensor
        if not matcher.connect():
            print("Cannot proceed without sensor connection")
            return
        
        print("Place finger on sensor to start matching...")
        print("Press Ctrl+C to exit")
        print()
        
        # Continuous matching loop
        while True:
            # Perform real-time matching
            match_result, confidence = matcher.match_live_with_stored('finger1.bin')
            
            if match_result:
                print(f"MATCH - Confidence: {confidence}")
            else:
                print("NO MATCH")
    
    except KeyboardInterrupt:
        print("\nProgram stopped")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        matcher.disconnect()

if __name__ == "__main__":
    main()
