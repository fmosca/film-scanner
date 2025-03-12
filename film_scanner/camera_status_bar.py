"""
Camera status bar component for the Film Scanner application.
Displays real-time camera settings in style of professional camera viewfinders.
"""
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os


class CameraStatusBar:
    """
    Displays live camera settings below the viewfinder including:
    - Aperture
    - Shutter speed
    - ISO
    - Exposure warning
    """
    def __init__(self, parent, height=30, bg_color="#222222", text_color="#ffffff"):
        """
        Initialize the camera status bar.
        
        Args:
            parent: Parent tkinter container
            height: Height of the status bar in pixels
            bg_color: Background color of the status bar
            text_color: Text color for the status information
        """
        self.parent = parent
        self.height = height
        self.bg_color = bg_color
        self.text_color = text_color
        
        # Status values
        self.aperture = "F--"
        self.shutter_speed = "--\"" 
        self.iso = "ISO --"
        self.exposure_warning = ""  # Over/under exposure indicator
        self.focus_status = ""      # Focus confirmation
        
        # Create frame with fixed height
        self.frame = tk.Frame(
            parent, 
            height=height, 
            bg=bg_color,
            highlightthickness=1,
            highlightbackground="#111111"
        )
        self.frame.pack(side=tk.TOP, fill=tk.X)
        self.frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Create canvas for custom drawing
        self.canvas = tk.Canvas(
            self.frame, 
            height=height, 
            bg=bg_color,
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Initialize display
        self.canvas_width = 0
        self.canvas_height = 0
        self.canvas.bind("<Configure>", self._on_resize)
        
        # Try to load a better font if available
        self.font_path = self._find_monospace_font()
        
        # Default PhotoImage (will be replaced in update)
        self.photo_image = None
        
        # Initial render
        self.update()

    def _find_monospace_font(self):
        """Try to find a suitable monospace font on the system"""
        # Common monospace font paths
        font_paths = [
            # Linux
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            # macOS
            "/Library/Fonts/Courier New.ttf",
            "/Library/Fonts/Monaco.ttf",
            # Windows
            "C:\\Windows\\Fonts\\consola.ttf",
            "C:\\Windows\\Fonts\\cour.ttf",
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                return path
        
        return None  # Fall back to default

    def _on_resize(self, event):
        """Handle resizing of the canvas"""
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.update()
        
    def update(self, aperture=None, shutter_speed=None, iso=None, 
               exposure_warning=None, focus_status=None):
        """
        Update the status bar with new camera values.
        
        Args:
            aperture: Aperture value (e.g., "F2.8")
            shutter_speed: Shutter speed (e.g., "1/60")
            iso: ISO sensitivity (e.g., "ISO 200")
            exposure_warning: Exposure warning indicator (e.g., "+2.0")
            focus_status: Focus status indicator (e.g., "●" for focused)
        """
        # Update values if provided
        if aperture is not None:
            self.aperture = aperture
        if shutter_speed is not None:
            self.shutter_speed = shutter_speed
        if iso is not None:
            self.iso = iso
        if exposure_warning is not None:
            self.exposure_warning = exposure_warning
        if focus_status is not None:
            self.focus_status = focus_status
            
        # Skip if canvas not sized yet
        if not hasattr(self, 'canvas_width') or self.canvas_width == 0:
            return
            
        # Create a new image for the status bar
        img = Image.new('RGB', (self.canvas_width, self.canvas_height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Choose font
        try:
            if self.font_path:
                # Try to use system monospace font
                font = ImageFont.truetype(self.font_path, 18)
            else:
                # Fall back to default
                font = ImageFont.load_default()
        except Exception:
            # Ultimate fallback
            font = ImageFont.load_default()
            
        # For default font, we need to ensure it's rendered larger
        if font == ImageFont.load_default():
            font = ImageFont.load_default().font_variant(size=16)
            
        # Calculate positions (divide width into sections)
        width = self.canvas_width
        padding = 10
        section_width = (width - (padding * 2)) / 4
        # Draw the status information
        # ISO (left)
        draw.text((padding, 5), self.iso, fill=self.text_color, font=font)
        
        # Shutter Speed (center-left)
        draw.text((padding + section_width, 5), self.shutter_speed, 
                  fill=self.text_color, font=font)
        
        # Aperture (center-right)
        draw.text((padding + section_width * 2, 5), self.aperture, 
                  fill=self.text_color, font=font)
        
        # Exposure Warning (right)
        warning_color = "#ffffff"  # Default white
        if self.exposure_warning:
            if self.exposure_warning.startswith("+"):
                warning_color = "#ff9900"  # Orange/amber for overexposure
            elif self.exposure_warning.startswith("-"):
                warning_color = "#00aaff"  # Blue for underexposure
                
            draw.text((padding + section_width * 3, 5), self.exposure_warning, 
                      fill=warning_color, font=font)
        
        # Focus indicator (small dot right of exposure warning if in focus)
        if self.focus_status == "focused":
            center_x = padding + section_width * 3.8
            center_y = self.canvas_height // 2
            radius = 5
            draw.ellipse((center_x - radius, center_y - radius, 
                          center_x + radius, center_y + radius), 
                         fill="#00ff00")  # Green dot
                
        # Convert to PhotoImage and update canvas
        self.photo_image = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo_image, anchor=tk.NW)
        
        # Force update
        self.canvas.update_idletasks()
