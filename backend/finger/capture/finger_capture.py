# R307 Fingerprint Sensor Capture Module
# This module captures fingerprint templates from R307 sensor on COM3

import serial
import time
import struct
import os
from datetime import datetime

class R307FingerCapture:
    """Interface for R307 fingerprint sensor communication"""
    
    # Command codes
    CMD_GET_IMAGE = 0x01
    CMD_IMG_2_TZ = 0x02
    CMD_UP_CHAR = 0x08
    
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
        
    def connect_sensor(self):
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
    
    def get_image(self):
        """Capture fingerprint image from sensor"""
        print("Place finger on sensor...")
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_GET_IMAGE]))
        
        packet_type, data = self._read_packet()
        if packet_type == self.FINGERPRINT_ACKPACKET and len(data) > 0:
            response_code = data[0]
            if response_code == self.FINGERPRINT_OK:
                print("✅ Fingerprint image captured successfully")
                return True
            elif response_code == self.FINGERPRINT_NOFINGER:
                print("❌ No finger detected on sensor")
                return False
            elif response_code == self.FINGERPRINT_IMAGEFAIL:
                print("❌ Failed to capture clear image")
                return False
            else:
                print(f"❌ Image capture failed with code: {response_code}")
                return False
        return False
    
    def image_2_template(self, buffer_id=1):
        """Convert captured image to template in specified buffer"""
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_IMG_2_TZ, buffer_id]))
        
        packet_type, data = self._read_packet()
        if packet_type == self.FINGERPRINT_ACKPACKET and len(data) > 0:
            response_code = data[0]
            if response_code == self.FINGERPRINT_OK:
                print(f"✅ Template generated in buffer {buffer_id}")
                return True
            elif response_code == self.FINGERPRINT_IMAGEMESS:
                print("❌ Image too messy to generate template")
                return False
            elif response_code == self.FINGERPRINT_FEATUREFAIL:
                print("❌ Could not identify fingerprint features")
                return False
            else:
                print(f"❌ Template generation failed with code: {response_code}")
                return False
        return False
    
    def upload_template(self, buffer_id=1):
        """Upload template from sensor buffer to computer"""
        print(f"💾 Uploading template from buffer {buffer_id}...")
        self._write_packet(self.FINGERPRINT_COMMANDPACKET, bytes([self.CMD_UP_CHAR, buffer_id]))
        
        # Read ACK packet
        packet_type, data = self._read_packet()
        if packet_type != self.FINGERPRINT_ACKPACKET or len(data) == 0 or data[0] != self.FINGERPRINT_OK:
            print("❌ Failed to initiate template upload")
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
                print("❌ Unexpected packet type during template upload")
                return None
        
        print(f"✅ Template uploaded successfully ({len(template_data)} bytes)")
        return template_data
    
    def capture_fingerprint_template(self, user_name, save_path="../../../dataset"):
        """Capture fingerprint template and save as .bin file"""
        if not self.connect_sensor():
            return False
            
        try:
            print(f"\n=== Fingerprint Capture for {user_name} ===")
            
            # Step 1: Capture image
            max_attempts = 10
            for attempt in range(max_attempts):
                print(f"Attempt {attempt + 1}/{max_attempts}")
                if self.get_image():
                    break
                time.sleep(0.5)
            else:
                print("❌ Failed to capture fingerprint image after multiple attempts")
                return False
            
            # Step 2: Convert to template
            if not self.image_2_template(buffer_id=1):
                print("❌ Failed to generate template from image")
                return False
            
            # Step 3: Upload template
            template_data = self.upload_template(buffer_id=1)
            if not template_data:
                print("❌ Failed to upload template")
                return False
            
            # Step 4: Save template as .bin file in the same folder as face images
            user_folder = os.path.join(save_path, user_name)
            
            # Ensure user folder exists
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)
            
            fingerprint_filename = "fingerprint.bin"
            fingerprint_path = os.path.join(user_folder, fingerprint_filename)
            
            with open(fingerprint_path, 'wb') as f:
                f.write(template_data)
            
            print(f"✅ Fingerprint template saved: {fingerprint_filename}")
            print(f"📁 Location: {fingerprint_path}")
            print(f"📊 File size: {len(template_data)} bytes")
            
            # Update user info file
            self._update_user_info(user_folder)
            
            return True
                
        except Exception as e:
            print(f"❌ Error during fingerprint capture: {e}")
            return False
        finally:
            if self.serial_conn:
                self.disconnect()
    
    def capture_fingerprint_template_data(self, user_name):
        """Capture fingerprint template and return binary data for MongoDB storage"""
        if not self.connect_sensor():
            return None
            
        try:
            print(f"\n=== Fingerprint Capture for {user_name} ===")
            
            # Step 1: Capture image
            max_attempts = 10
            for attempt in range(max_attempts):
                print(f"Attempt {attempt + 1}/{max_attempts}")
                if self.get_image():
                    break
                time.sleep(0.5)
            else:
                print("❌ Failed to capture fingerprint image after multiple attempts")
                return None
            
            # Step 2: Convert to template
            if not self.image_2_template(buffer_id=1):
                print("❌ Failed to generate template from image")
                return None
            
            # Step 3: Upload template
            template_data = self.upload_template(buffer_id=1)
            if not template_data:
                print("❌ Failed to upload template")
                return None
            
            print(f"✅ Fingerprint template captured ({len(template_data)} bytes)")
            return template_data
                
        except Exception as e:
            print(f"❌ Error during fingerprint capture: {e}")
            return None
        finally:
            if self.serial_conn:
                self.disconnect()
    
    
    def _update_user_info(self, user_folder):
        """Update user info file to include fingerprint data"""
        user_info_path = os.path.join(user_folder, "user_info.txt")
        
        if os.path.exists(user_info_path):
            # Read existing content
            with open(user_info_path, 'r') as f:
                content = f.read()
            
            # Add fingerprint info
            with open(user_info_path, 'w') as f:
                f.write(content)
                f.write(f"Fingerprint: Captured\n")
                f.write(f"Fingerprint Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Sensor: R307 on {self.port}\n")

def main():
    """Test function for fingerprint capture"""
    user_name = input("Enter user name: ").strip()
    if not user_name:
        print("Please enter a valid name")
        return
    
    finger_capture = R307FingerCapture()
    success = finger_capture.capture_fingerprint_template(user_name)
    
    if success:
        print(f"🎉 Fingerprint captured successfully for {user_name}!")
    else:
        print(f"❌ Failed to capture fingerprint for {user_name}")

if __name__ == "__main__":
    main()
