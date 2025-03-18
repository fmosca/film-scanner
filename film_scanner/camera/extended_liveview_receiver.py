"""
Extended LiveView Receiver with camera status information extraction.
Extends functionality to parse metadata from camera stream.
"""
import socket
import time
import threading
import struct
import queue
from olympuswifi.liveview import LiveViewReceiver


class ExtendedLiveViewReceiver:
    """
    Extended version of LiveViewReceiver that extracts camera settings.
    Adds camera status extraction from RTP headers while maintaining
    compatibility with the original LiveViewReceiver.
    """
    
    def __init__(self, img_queue, status_queue=None):
        """
        Initialize the extended live view receiver.
        
        Args:
            img_queue: Queue to put received frames
            status_queue: Queue to put camera status info (optional)
        """
        self.img_queue = img_queue
        self.status_queue = status_queue
        self.lock = threading.Lock()
        self.running = True
        self.socket = None
        
        # Tracking state for frame assembly
        self.frame_data = bytearray()
        self.has_jpeg_header = False
        self.current_frame_seq = -1
        
        # Tracking latest camera settings
        self.camera_settings = {}
        self.last_rtp_extension = None
    
    def update_packet_data(self, rtp_extension_data):
        """
        Process RTP extension data and extract camera settings.
        
        Args:
            rtp_extension_data: Raw extension header bytes
        """
        if not rtp_extension_data:
            return
            
        # Store raw data for debugging
        self.last_rtp_extension = rtp_extension_data
        
        try:
            # Extract settings from extension data
            settings = self._parse_extension_data(rtp_extension_data)
            
            # Only update our camera_settings dict with non-empty values
            for key, value in settings.items():
                if value:
                    self.camera_settings[key] = value
            
            # If we have a status queue, send the updated settings
            if self.status_queue is not None and settings:
                try:
                    # Try to update without blocking
                    if self.status_queue.full():
                        # Remove old status to avoid backlog
                        try:
                            self.status_queue.get_nowait()
                        except queue.Empty:
                            pass
                    
                    # Put the full current settings (not just the updates)
                    self.status_queue.put_nowait(self.camera_settings.copy())
                except queue.Full:
                    # Skip this update if queue is still full
                    pass
        except Exception as e:
            print(f"Error parsing extension data: {e}")
    
    def _parse_extension_data(self, extension_data):
        """
        Parse camera settings from extension data.
        
        Args:
            extension_data: RTP extension data
            
        Returns:
            dict: Extracted camera settings
        """
        settings = {}
        
        try:
            # Function IDs and their field positions
            FUNC_ID_ORIENTATION = 4    # Orientation data
            FUNC_ID_APERTURE = 9       # Aperture (F-number)
            FUNC_ID_SHUTTER = 8        # Shutter speed
            FUNC_ID_ISO = 12           # ISO value
            FUNC_ID_EXP_COMP = 10      # Exposure compensation
            
            idx = 0
            while idx + 4 <= len(extension_data):
                # Each function block starts with function ID and length
                if idx + 4 > len(extension_data):
                    break
                    
                func_id = (extension_data[idx] << 8) + extension_data[idx+1]
                length = (extension_data[idx+2] << 8) + extension_data[idx+3]
                field_length = 4 * length
                idx += 4
                
                if idx + field_length > len(extension_data):
                    break
                
                # Process based on function ID
                if func_id == FUNC_ID_APERTURE and idx + 8 <= len(extension_data):
                    # F-number is typically stored as value * 100
                    f_value = struct.unpack('>I', extension_data[idx+4:idx+8])[0]
                    if f_value > 0:
                        settings['aperture'] = f"F{f_value/100:.1f}"
                
                elif func_id == FUNC_ID_SHUTTER and idx + 8 <= len(extension_data):
                    # Shutter speed can be complex - check format based on camera model
                    num, denom = struct.unpack('>II', extension_data[idx:idx+8])
                    if num > 0 and denom > 0:
                        if num > denom:
                            # Slower than 1 second
                            if denom == 1:
                                settings['shutter_speed'] = f"{num}\""
                            else:
                                seconds = num / denom
                                settings['shutter_speed'] = f"{seconds:.1f}\""
                        else:
                            # Faster than 1 second
                            settings['shutter_speed'] = f"1/{denom/num:.0f}\""
                
                elif func_id == FUNC_ID_ISO and idx + 8 <= len(extension_data):
                    # ISO value and auto flag
                    iso_value = struct.unpack('>I', extension_data[idx:idx+4])[0]
                    iso_auto = struct.unpack('>H', extension_data[idx+4:idx+6])[0] != 0
                    
                    if iso_value > 0:
                        if iso_auto:
                            settings['iso'] = f"ISO-A {iso_value}"
                        else:
                            settings['iso'] = f"ISO {iso_value}"
                
                elif func_id == FUNC_ID_EXP_COMP and idx + 8 <= len(extension_data):
                    # Exposure compensation * 10
                    exp_value = struct.unpack('>i', extension_data[idx+4:idx+8])[0]
                    if exp_value != 0:
                        value = exp_value / 10.0
                        sign = "+" if value > 0 else ""
                        settings['exposure_compensation'] = f"{sign}{value:.1f}"
                    else:
                        settings['exposure_compensation'] = "±0.0"
                
                elif func_id == FUNC_ID_ORIENTATION and idx + 4 <= len(extension_data):
                    # Orientation value
                    orientation = extension_data[idx+3]
                    if orientation in [1, 3, 6, 8]:
                        settings['orientation'] = orientation
                
                # Move to next field
                idx += field_length
        
        except Exception as e:
            print(f"Error parsing extension data block: {e}")
        
        return settings
    
    def receive_packets(self, port):
        """
        Receive and process RTP packets from the camera.
        
        Args:
            port: UDP port to listen on
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(0.5)  # Set a timeout for the socket
        
        self.running = True
        
        # Try to bind the socket to the port
        try:
            self.socket.bind(('0.0.0.0', port))
        except Exception as e:
            print(f"Failed to bind socket on port {port}: {e}")
            self.running = False
            return
            
        # Process incoming packets
        while self.running:
            try:
                # Receive a packet
                packet_data, _ = self.socket.recvfrom(65536)
                
                # Process the packet
                self._process_packet(packet_data)
                
            except socket.timeout:
                # This is normal, just continue
                continue
            except Exception as e:
                print(f"Error receiving packet: {e}")
                time.sleep(0.1)  # Avoid tight loop on error
        
        # Clean up
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
    
    def _process_packet(self, packet_data):
        """
        Process an RTP packet.
        
        Args:
            packet_data: Raw RTP packet data
        """
        # Must have at least 12 bytes for RTP header
        if len(packet_data) < 12:
            return
        
        try:
            # Parse header fields
            first_byte = packet_data[0]
            has_extension = (first_byte & 0x10) != 0  # X bit
            marker = (packet_data[1] & 0x80) != 0     # M bit
            seq_num = (packet_data[2] << 8) | packet_data[3]
            timestamp = struct.unpack('>I', packet_data[4:8])[0]
            
            # Extract payload
            payload_start = 12  # Basic RTP header is 12 bytes
            
            # Handle extension header if present
            if has_extension:
                if payload_start + 4 <= len(packet_data):
                    # Get extension header length
                    ext_header_len = struct.unpack('>H', packet_data[payload_start+2:payload_start+4])[0]
                    ext_header_len = ext_header_len * 4 + 4  # Convert to bytes
                    
                    if payload_start + ext_header_len <= len(packet_data):
                        # Extract extension data
                        extension_data = packet_data[payload_start:payload_start+ext_header_len]
                        
                        # Process extension data in the first packet of a frame
                        if timestamp != self.current_frame_seq:
                            self.update_packet_data(extension_data)
                        
                        # Adjust payload start
                        payload_start += ext_header_len
            
            # Extract payload
            if payload_start < len(packet_data):
                payload = packet_data[payload_start:]
            else:
                payload = b''
            
            # Check if this is the start of a new frame
            if timestamp != self.current_frame_seq:
                # If we had a previous frame in progress, add it to the queue if complete
                if self.has_jpeg_header and len(self.frame_data) > 0:
                    # Check if the frame ends with JPEG marker
                    if len(self.frame_data) >= 2 and self.frame_data[-2] == 0xFF and self.frame_data[-1] == 0xD9:
                        self._add_frame_to_queue(self.frame_data)
                
                # Start new frame
                self.frame_data = bytearray()
                self.has_jpeg_header = False
                self.current_frame_seq = timestamp
            
            # Process payload - check for JPEG header
            if len(payload) >= 2 and payload[0] == 0xFF and payload[1] == 0xD8:
                self.has_jpeg_header = True
            
            # Add payload to current frame if it has a JPEG header
            if self.has_jpeg_header and payload:
                self.frame_data.extend(payload)
            
            # If this is the last packet of the frame
            if marker and self.has_jpeg_header and len(self.frame_data) > 0:
                # Check if the frame ends with JPEG marker
                if len(self.frame_data) >= 2 and self.frame_data[-2] == 0xFF and self.frame_data[-1] == 0xD9:
                    self._add_frame_to_queue(self.frame_data)
                
                # Reset for next frame
                self.frame_data = bytearray()
                self.has_jpeg_header = False
        
        except Exception as e:
            print(f"Error processing packet: {e}")
    
    def _add_frame_to_queue(self, frame_data):
        """
        Add a complete frame to the queue.
        
        Args:
            frame_data: Complete JPEG frame data
        """
        try:
            # Create frame object compatible with LiveViewReceiver
            frame = LiveViewReceiver.JPEGandExtension(bytes(frame_data), self.last_rtp_extension)
            
            # Add to queue, avoiding blocking
            try:
                if self.img_queue.full():
                    # Remove oldest frame to make room
                    try:
                        self.img_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                self.img_queue.put_nowait(frame)
            except queue.Full:
                # Skip this frame if queue is still full
                pass
        except Exception as e:
            print(f"Error adding frame to queue: {e}")
    
    def shut_down(self):
        """Shut down the receiver."""
        with self.lock:
            self.running = False
        
        # Close socket if open
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
    
    def get_latest_camera_settings(self):
        """
        Get the latest camera settings.
        
        Returns:
            dict: Latest camera settings
        """
        return self.camera_settings.copy()
