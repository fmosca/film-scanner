"""
Extended LiveView Receiver with camera status information extraction.
Extends the olympuswifi.liveview.LiveViewReceiver class to parse metadata.
"""
import socket
import time
import threading
import struct
import queue
from olympuswifi.liveview import LiveViewFrame
from film_scanner.rtp_packet_parser import RtpPacketParser


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
        self.s = None
        self.packet_parser = RtpPacketParser()
        
        # Tracking latest camera settings
        self.camera_settings = {}
        
    def update_packet_data(self, rtp_extension_data):
        """
        Process RTP extension data and extract camera settings.
        
        Args:
            rtp_extension_data: Raw extension header bytes
        """
        if not rtp_extension_data:
            return
            
        # Parse the extension header
        settings = self.packet_parser.parse_extension_header(rtp_extension_data)
        
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
    
    def receive_packets(self, port):
        """
        Receive and process RTP packets from the camera.
        
        Args:
            port: UDP port to listen on
        """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.settimeout(0.5)  # Set a timeout for the socket
        
        self.running = True
        
        # Try to bind the socket to the port
        try:
            self.s.bind(('0.0.0.0', port))
        except Exception as e:
            print(f"Failed to bind socket on port {port}: {e}")
            self.running = False
            return
            
        # Variables for frame assembly
        frame_data = bytearray()
        has_jpeg_header = False
        current_frame_seq = -1
        
        # Process incoming packets
        while self.running:
            try:
                # Receive a packet (up to 65536 bytes)
                packet_data, _ = self.s.recvfrom(65536)
                
                # Must have at least 12 bytes for RTP header
                if len(packet_data) < 12:
                    continue
                
                # Parse RTP header
                # 0                   1                   2                   3
                # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
                # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                # |V=2|P|X|  CC   |M|     PT      |       sequence number         |
                # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                # |                           timestamp                           |
                # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                # |           synchronization source (SSRC) identifier            |
                # +=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+
                
                # Parse header fields
                first_byte = packet_data[0]
                has_extension = (first_byte & 0x10) != 0  # X bit
                marker = (packet_data[1] & 0x80) != 0    # M bit
                seq_num = struct.unpack('>H', packet_data[2:4])[0]  # Sequence number
                timestamp = struct.unpack('>I', packet_data[4:8])[0]  # Timestamp
                
                # Extract payload
                payload_start = 12  # Basic RTP header is 12 bytes
                
                # Handle extension header if present
                extension_data = None
                if has_extension:
                    # Extension header format:
                    # 0                   1                   2                   3
                    # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
                    # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                    # |      defined by profile       |           length              |
                    # +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
                    # |                        header extension                       |
                    # |                              ...                              |
                    
                    # Extract extension header
                    ext_header_len = struct.unpack('>H', packet_data[payload_start+2:payload_start+4])[0]
                    ext_header_len = ext_header_len * 4 + 4  # Length in 32-bit words plus header
                    
                    # Get the extension data
                    extension_data = packet_data[payload_start:payload_start+ext_header_len]
                    
                    # Process extension data in the first packet of a frame
                    if timestamp != current_frame_seq:
                        self.update_packet_data(extension_data)
                    
                    # Adjust payload start to skip extension header
                    payload_start += ext_header_len
                
                # Extract the payload
                payload = packet_data[payload_start:]
                
                # Check if this is the start of a new frame
                if timestamp != current_frame_seq:
                    # If we had a previous frame in progress, add it to the queue
                    if has_jpeg_header and len(frame_data) > 0:
                        self._add_frame_to_queue(frame_data)
                    
                    # Start new frame
                    frame_data = bytearray()
                    has_jpeg_header = False
                    current_frame_seq = timestamp
                
                # Process the payload
                # Detect JPEG header (0xFF, 0xD8)
                if len(payload) >= 2 and payload[0] == 0xFF and payload[1] == 0xD8:
                    has_jpeg_header = True
                
                # Add payload to current frame
                if has_jpeg_header:
                    frame_data.extend(payload)
                
                # If this is the last packet of the frame
                if marker and has_jpeg_header:
                    self._add_frame_to_queue(frame_data)
                    frame_data = bytearray()
                    has_jpeg_header = False
                
            except socket.timeout:
                # This is normal, just continue
                continue
            except Exception as e:
                print(f"Error receiving packet: {e}")
                time.sleep(0.1)  # Avoid tight loop on error
        
        # Clean up
        if self.s:
            self.s.close()
            self.s = None
    
    def _add_frame_to_queue(self, frame_data):
        """
        Add a complete frame to the queue.
        
        Args:
            frame_data: JPEG data for the frame
        """
        try:
            # Check if we have a complete JPEG (ends with 0xFF, 0xD9)
            if len(frame_data) >= 2 and frame_data[-2] == 0xFF and frame_data[-1] == 0xD9:
                # Create a frame object
                frame = LiveViewFrame(bytes(frame_data))
                
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
        if self.s:
            try:
                self.s.close()
            except Exception:
                pass
            self.s = None
    
    def get_latest_camera_settings(self):
        """
        Get the latest camera settings.
        
        Returns:
            dict: Latest camera settings
        """
        return self.camera_settings.copy()
