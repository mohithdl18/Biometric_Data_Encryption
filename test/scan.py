#!/usr/bin/env python3
"""
R307 Fingerprint Sensor Interface
Captures fingerprint templates from R307 sensor and stores them locally as .bin files
instead of storing on the sensor itself.

Hardware: R307 Fingerprint Sensor connected to COM3
Author: Created for fingerprint template extraction and local storage
"""

import serial
import time
import struct
import os
from datetime import datetime

class R307FingerprintSensor:
    """Interface for R307 fingerprint sensor communication"""
    
    # Command codes
    CMD_GET_IMAGE = 0x01
    CMD_IMG_2_TZ = 0x02
    CMD_TEMPLATE_NUM = 0x1D
    CMD_UP_CHAR = 0x08
    CMD_DOWN_CHAR = 0x09
    
    # Response codes
    FINGERPRINT_OK = 0x00
    FINGERPRINT_PACKETRECIEVEERR = 0x01
    FINGERPRINT_NOFINGER = 0x02
    FINGERPRINT_IMAGEFAIL = 0x03
    FINGERPRINT_IMAGEMESS = 0x06
    FINGERPRINT_FEATUREFAIL = 0x07
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
    
    def get_image(self):
        """Capture fingerprint image from sensor"""
        print("Place finger on sensor...")
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_GET_IMAGE]))
        
        packet_type, data = self._read_packet()
        if packet_type == self.FINGERPRINT_ACKPACKET and len(data) > 0:
            response_code = data[0]
            if response_code == self.FINGERPRINT_OK:
                print("Fingerprint image captured successfully")
                return True
            elif response_code == self.FINGERPRINT_NOFINGER:
                print("No finger detected on sensor")
                return False
            elif response_code == self.FINGERPRINT_IMAGEFAIL:
                print("Failed to capture clear image")
                return False
            else:
                print(f"Image capture failed with code: {response_code}")
                return False
        return False
    
    def image_2_template(self, buffer_id=1):
        """Convert captured image to template in specified buffer"""
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_IMG_2_TZ, buffer_id]))
        
        packet_type, data = self._read_packet()
        if packet_type == self.FINGERPRINT_ACKPACKET and len(data) > 0:
            response_code = data[0]
            if response_code == self.FINGERPRINT_OK:
                print(f"Template generated in buffer {buffer_id}")
                return True
            elif response_code == self.FINGERPRINT_IMAGEMESS:
                print("Image too messy to generate template")
                return False
            elif response_code == self.FINGERPRINT_FEATUREFAIL:
                print("Could not identify fingerprint features")
                return False
            else:
                print(f"Template generation failed with code: {response_code}")
                return False
        return False
    
    def upload_template(self, buffer_id=1):
        """Upload template from sensor buffer to computer"""
        print(f"Uploading template from buffer {buffer_id}...")
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_UP_CHAR, buffer_id]))
        
        # Read ACK packet
        packet_type, data = self._read_packet()
        if packet_type != self.FINGERPRINT_ACKPACKET or len(data) == 0 or data[0] != self.FINGERPRINT_OK:
            print("Failed to initiate template upload")
            return None
        
        # Read template data packets
        template_data = b''
        while True:
            packet_type, data = self._read_packet()
            if packet_type == self.FINGERPRINT_DATAPACKET:
                template_data += data
            elif packet_type == self.FINGERPRINT_ENDDATAPACKET:
                template_data += data
                break
            else:
                print("Unexpected packet type during template upload")
                return None
        
        print(f"Template uploaded successfully ({len(template_data)} bytes)")
        return template_data
    
    def scan_and_store_template(self, filename=None):
        """Complete workflow: scan finger, generate template, and store to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fingerprint_{timestamp}.bin"
        
        # Ensure .bin extension
        if not filename.endswith('.bin'):
            filename += '.bin'
        
        print("=== Fingerprint Template Capture ===")
        
        # Step 1: Capture image
        max_attempts = 10
        for attempt in range(max_attempts):
            print(f"Attempt {attempt + 1}/{max_attempts}")
            if self.get_image():
                break
            time.sleep(0.5)
        else:
            print("Failed to capture fingerprint image after multiple attempts")
            return False
        
        # Step 2: Convert to template
        if not self.image_2_template(buffer_id=1):
            print("Failed to generate template from image")
            return False
        
        # Step 3: Upload template
        template_data = self.upload_template(buffer_id=1)
        if not template_data:
            print("Failed to upload template")
            return False
        
        # Step 4: Save to file
        try:
            with open(filename, 'wb') as f:
                f.write(template_data)
            print(f"Template saved to: {filename}")
            print(f"File size: {len(template_data)} bytes")
            return True
        except Exception as e:
            print(f"Failed to save template to file: {e}")
            return False

def main():
    """Main function to demonstrate fingerprint scanning and storage"""
    print("R307 Fingerprint Template Scanner")
    print("=================================")
    
    # Create sensor instance
    sensor = R307FingerprintSensor(port='COM3')
    
    try:
        # Connect to sensor
        if not sensor.connect():
            print("Cannot proceed without sensor connection")
            return
        
        print("\nSensor connected successfully!")
        print("This program will scan your fingerprint and save the template locally.")
        print("The template will NOT be stored on the sensor.")
        
        while True:
            print("\nOptions:")
            print("1. Scan and save new fingerprint template")
            print("2. Scan with custom filename")
            print("3. Exit")
            
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == '1':
                print("\n--- Starting fingerprint scan ---")
                if sensor.scan_and_store_template():
                    print("✓ Fingerprint template saved successfully!")
                else:
                    print("✗ Failed to capture and save template")
                    
            elif choice == '2':
                filename = input("Enter filename for template (without .bin extension): ").strip()
                if filename:
                    print(f"\n--- Starting fingerprint scan for '{filename}' ---")
                    if sensor.scan_and_store_template(filename):
                        print("✓ Fingerprint template saved successfully!")
                    else:
                        print("✗ Failed to capture and save template")
                else:
                    print("Invalid filename")
                    
            elif choice == '3':
                print("Exiting...")
                break
                
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sensor.disconnect()
        print("Program ended")

if __name__ == "__main__":
    main()
