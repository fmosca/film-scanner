"""
RTP packet parser for extracting camera status data from Olympus camera live view stream.
Based on the Open Platform Camera protocol specification.
"""
import struct


class RtpPacketParser:
    """
    Parses RTP packets from Olympus cameras to extract metadata like:
    - Aperture (F-Number)
    - Shutter Speed
    - ISO Sensitivity
    - Exposure Warning
    - Focus Status
    
    Reference: Olympus Camera Protocol Documentation
    Function ID reference:
    - 0x08: Shutter Speed
    - 0x09: F-Number (Aperture)
    - 0x0A: Exposure Compensation
    - 0x0C: ISO Sensitivity
    - 0x10: Exposure Warning
    - 0x11: Focus Mode
    """
    
    # Function IDs for camera settings in RTP extension header
    FUNCTION_ID_SHUTTER_SPEED = 0x08
    FUNCTION_ID_APERTURE = 0x09
    FUNCTION_ID_EXPOSURE_COMPENSATION = 0x0A
    FUNCTION_ID_ISO_SENSITIVITY = 0x0C
    FUNCTION_ID_EXPOSURE_WARNING = 0x10
    FUNCTION_ID_FOCUS_MODE = 0x11
    
    def __init__(self):
        self.shutter_speed = None
        self.aperture = None
        self.iso = None
        self.exposure_comp = None
        self.exposure_warning = None
        self.focus_mode = None
        
    def parse_extension_header(self, extension_data):
        """
        Parse the RTP extension header to extract camera status information.
        
        Args:
            extension_data: Raw extension header bytes
            
        Returns:
            dict: Extracted camera settings
        """
        if not extension_data or len(extension_data) < 4:
            return {}
        
        # Parse header fields
        try:
            # First 4 bytes contain version and length
            version, length = struct.unpack('>HH', extension_data[:4])
            
            # Process each information field
            position = 4  # Start after header
            end_position = 4 + (length * 4)  # Length is in 32-bit words
            
            settings = {}
            
            while position + 4 <= len(extension_data) and position < end_position:
                # Each field starts with function_id (2 bytes) and length (2 bytes)
                if position + 4 > len(extension_data):
                    break
                    
                function_id, field_length = struct.unpack('>HH', extension_data[position:position+4])
                position += 4
                
                # Process based on function ID
                if function_id == self.FUNCTION_ID_SHUTTER_SPEED and position + 12 <= len(extension_data):
                    settings.update(self._parse_shutter_speed(extension_data[position:position+12]))
                
                elif function_id == self.FUNCTION_ID_APERTURE and position + 12 <= len(extension_data):
                    settings.update(self._parse_aperture(extension_data[position:position+12]))
                
                elif function_id == self.FUNCTION_ID_ISO_SENSITIVITY and position + 12 <= len(extension_data):
                    settings.update(self._parse_iso_sensitivity(extension_data[position:position+12]))
                    
                elif function_id == self.FUNCTION_ID_EXPOSURE_COMPENSATION and position + 12 <= len(extension_data):
                    settings.update(self._parse_exposure_compensation(extension_data[position:position+12]))
                    
                elif function_id == self.FUNCTION_ID_EXPOSURE_WARNING and position + 4 <= len(extension_data):
                    settings.update(self._parse_exposure_warning(extension_data[position:position+4]))
                    
                elif function_id == self.FUNCTION_ID_FOCUS_MODE and position + 4 <= len(extension_data):
                    settings.update(self._parse_focus_mode(extension_data[position:position+4]))
                
                # Move to next field
                position += field_length * 4  # Length is in 32-bit words
            
            # Update instance variables
            if 'shutter_speed' in settings:
                self.shutter_speed = settings['shutter_speed']
            if 'aperture' in settings:
                self.aperture = settings['aperture']
            if 'iso' in settings:
                self.iso = settings['iso']
            if 'exposure_compensation' in settings:
                self.exposure_comp = settings['exposure_compensation']
            if 'exposure_warning' in settings:
                self.exposure_warning = settings['exposure_warning']
            if 'focus_mode' in settings:
                self.focus_mode = settings['focus_mode']
                
            return settings
            
        except Exception as e:
            print(f"Error parsing RTP extension header: {e}")
            return {}
    
    def _parse_shutter_speed(self, data):
        """Parse shutter speed information (3 words, 12 bytes)"""
        try:
            # Format: numerator/denominator for current value (bytes 8-15)
            if len(data) < 12:
                return {'shutter_speed': '---'}
                
            # Try different offsets for shutter speed data
            try:
                numerator, denominator = struct.unpack('>II', data[8:16])
            except struct.error:
                try:
                    numerator, denominator = struct.unpack('>II', data[4:12])
                except struct.error:
                    return {'shutter_speed': '---'}
            
            if numerator == 0 or denominator == 0:
                return {'shutter_speed': '---'}
            
            # Debug print to see raw values
            print(f"Shutter speed raw: {numerator}/{denominator}")
                
            # Format the shutter speed display
            if numerator > denominator:
                # Longer than 1 second (e.g., 2")
                seconds = float(numerator) / float(denominator)
                if denominator == 1:
                    formatted = f"{numerator}\""
                else:
                    formatted = f"{seconds:.1f}\""
            else:
                # Fraction of a second (e.g., 1/60)
                if numerator == 1:
                    formatted = f"1/{int(denominator)}"
                else:
                    fraction = denominator / numerator
                    formatted = f"1/{fraction:.1f}"
                    
            return {'shutter_speed': formatted}
        except Exception:
            return {'shutter_speed': '---'}
    
    def _parse_aperture(self, data):
        """Parse aperture (F-number) information (3 words, 12 bytes)"""
        try:
            # Current F-number is in the third word (bytes 8-11)
            # It's a 10x value (e.g., 28 means F2.8)
            aperture_value = struct.unpack('>I', data[8:12])[0]
            
            if aperture_value == 0:
                return {'aperture': 'F--'}
                
            formatted = f"F{aperture_value / 10:.1f}"
            return {'aperture': formatted}
        except Exception:
            return {'aperture': 'F--'}
    
    def _parse_iso_sensitivity(self, data):
        """Parse ISO sensitivity information (3 words, 12 bytes)"""
        try:
            # ISO value is in the first word (bytes 0-3)
            # Auto flag is in the second word (bytes 4-7, first 16 bits)
            iso_value = struct.unpack('>I', data[0:4])[0]
            auto_flag = (struct.unpack('>H', data[4:6])[0] != 0)
            
            # Extended ISO warning is the rest of the second word
            # extended_warning = (struct.unpack('>H', data[6:8])[0] != 0)
            
            if iso_value == 0:
                return {'iso': 'ISO --'}
                
            # Special case for LOW ISO
            if iso_value == 0xFFFE:
                if auto_flag:
                    formatted = "ISO-A LOW"
                else:
                    formatted = "ISO LOW"
            else:
                if auto_flag:
                    formatted = f"ISO-A {iso_value}"
                else:
                    formatted = f"ISO {iso_value}"
                    
            return {'iso': formatted}
        except Exception:
            return {'iso': 'ISO --'}
    
    def _parse_exposure_compensation(self, data):
        """Parse exposure compensation information (3 words, 12 bytes)"""
        try:
            # Current value is in the third word (bytes 8-11)
            exp_comp_value = struct.unpack('>i', data[8:12])[0]  # Signed 32-bit integer
            
            # Olympus stores this as 10x the actual value
            actual_value = exp_comp_value / 10.0
            
            if abs(actual_value) < 0.1:  # Very close to zero
                return {'exposure_compensation': '±0.0'}
                
            sign = "+" if actual_value > 0 else ""
            formatted = f"{sign}{actual_value:.1f}"
            return {'exposure_compensation': formatted}
        except Exception:
            return {'exposure_compensation': ''}
    
    def _parse_exposure_warning(self, data):
        """Parse exposure warning information (1 word, 4 bytes)"""
        try:
            # Exposure warning is the whole word (4 bytes)
            warning_value = struct.unpack('>I', data[0:4])[0]
            
            if warning_value == 0:
                return {'exposure_warning': ''}
            else:
                # This is just a flag, not a value
                return {'exposure_warning': 'EXP!'}
        except Exception:
            return {'exposure_warning': ''}
    
    def _parse_focus_mode(self, data):
        """Parse focus mode information (1 word, 4 bytes)"""
        try:
            # Focus type is the first 16 bits
            focus_type = struct.unpack('>H', data[0:2])[0]
            
            focus_modes = {
                0: "S-AF",  # Single AF
                1: "C-AF",  # Continuous AF
                2: "MF",    # Manual Focus
            }
            
            focus_mode = focus_modes.get(focus_type, "")
            
            # Just determine if we're in focus (for simplicity)
            # A more sophisticated implementation would consider the AF frame info
            focus_status = "unknown"
            
            return {
                'focus_mode': focus_mode,
                'focus_status': focus_status
            }
        except Exception:
            return {
                'focus_mode': '',
                'focus_status': 'unknown'
            }
    
    def get_all_settings(self):
        """Get all currently parsed settings as a dictionary"""
        return {
            'shutter_speed': self.shutter_speed,
            'aperture': self.aperture,
            'iso': self.iso,
            'exposure_compensation': self.exposure_comp,
            'exposure_warning': self.exposure_warning,
            'focus_mode': self.focus_mode
        }
