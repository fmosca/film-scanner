"""
Main application module for the Film Scanner application.
Coordinates UI, camera, and preview components.
"""
import os
import time
import tkinter as tk
import tkinter.messagebox
from PIL import Image
import io
from .camera_manager import CameraManager
from .preview_manager import PreviewManager


class FilmScannerApp:
    """
    Main application class that manages the UI and coordinates between components.
    """
    def __init__(self, root):
        """
        Initialize the application.
        
        Args:
            root: Root tkinter window
        """
        self.window = root
        self.window.title("Film Negative Scanner")
        
        # Create output directory
        self.output_directory = os.path.expanduser("~/Pictures/FilmScans")
        if not os.path.exists(self.output_directory):
            os.makedirs(self.output_directory)
        
        # State variables
        self.current_mode = "live_view"  # Can be 'live_view' or 'preview'
        self.latest_image_path = None
        
        # Initialize components
        self.camera_manager = CameraManager()
        
        # Create UI elements
        self.status_bar = tk.Label(self.window, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.TOP, fill=tk.X)
        
        self.info_frame = tk.Frame(self.window, height=50)
        self.info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.info_label = tk.Label(self.info_frame, text="Live View", anchor=tk.W, padx=10)
        self.info_label.pack(side=tk.LEFT)
        
        self.shortcut_label = tk.Label(
            self.info_frame, 
            text="S: Shoot | F: Focus Peaking | Z: Zoom | ESC: Quit | ?: Help", 
            anchor=tk.E, 
            padx=10
        )
        self.shortcut_label.pack(side=tk.RIGHT)
        
        # Initialize preview manager after UI elements
        self.preview_manager = PreviewManager(self.window, self.status_bar, self.info_frame)
        
        # Set initial window size
        self.window.geometry("800x600")
        
        # Bind keyboard shortcuts
        self.bind_keys()
        
        # Show instructions
        self.show_instructions()
        
        # Start live view automatically
        self.start_live_view()
        
        # Start checking for frame updates
        self.window.after(25, self.check_live_view_updates)
    
    def update_status(self, message):
        """Update status bar message."""
        self.status_bar.config(text=message)
        self.window.update_idletasks()  # Force GUI update
    
    def show_instructions(self):
        """Show application instructions."""
        instructions = """
        Film Negative Scanner - Keyboard Controls
        
        S         - Take photo when in live view / Accept and download when in preview
        F         - Toggle focus peaking
        Z         - Toggle zoom (cycles between 1x, 3x, 5x, 7x, 10x)
        ESCAPE    - Quit the application
        R         - Reject preview and return to live view
        I         - Invert image colors (helpful for negative film)
        H or ?    - Show this help
        """
        self.update_status("Ready - Press S to take a photo")
        tk.messagebox.showinfo("Instructions", instructions)
    
    def bind_keys(self):
        """Bind keyboard shortcuts to functions."""
        self.window.bind("s", self.shoot_key_pressed)
        self.window.bind("S", self.shoot_key_pressed)
        self.window.bind("f", self.toggle_focus_peaking)
        self.window.bind("F", self.toggle_focus_peaking)
        self.window.bind("z", self.cycle_zoom)
        self.window.bind("Z", self.cycle_zoom)
        self.window.bind("<Escape>", lambda e: self.window.quit())
        self.window.bind("r", self.reject_preview)
        self.window.bind("R", self.reject_preview)
        self.window.bind("h", lambda e: self.show_instructions())
        self.window.bind("H", lambda e: self.show_instructions())
        self.window.bind("?", lambda e: self.show_instructions())
        self.window.bind("i", self.toggle_image_inversion)
        self.window.bind("I", self.toggle_image_inversion)
    
    def resize_window_for_image(self, width, height):
        """
        Resize window to fit an image with specified dimensions.
        
        Args:
            width: Image width
            height: Image height
        """
        # Get screen dimensions
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # Calculate status and info bar heights
        status_bar_height = self.status_bar.winfo_reqheight()
        info_frame_height = self.info_frame.winfo_reqheight()
        
        # Apply 5% margin to available screen space
        margin_percentage = 0.05
        available_width = int(screen_width * (1 - 2 * margin_percentage))
        available_height = int((screen_height - status_bar_height - info_frame_height) * (1 - 2 * margin_percentage))
        
        # Calculate scaling
        width_ratio = available_width / width
        height_ratio = available_height / height
        
        # Use the smaller scaling to fit entirely on screen
        scale_factor = min(width_ratio, height_ratio)
        
        # Calculate new dimensions
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        # Set window size
        total_height = new_height + status_bar_height + info_frame_height
        self.window.geometry(f"{new_width}x{total_height}")
        
        # Center the window on screen
        x_position = int((screen_width - new_width) / 2)
        y_position = int((screen_height - total_height) / 2)
        self.window.geometry(f"+{x_position}+{y_position}")
    
    def start_live_view(self):
        """
        Start the live view streaming.
        
        Returns:
            bool: Success or failure
        """
        self.update_status("Starting live view...")
        if self.camera_manager.start_live_view():
            self.current_mode = "live_view"
            self.update_status("Live view active - Press S to take a photo")
            self.info_label.config(text="Live View")
            return True
        else:
            self.update_status("Failed to start live view")
            return False
    
    def check_live_view_updates(self):
        """Check for new frames in the live view queue and update display."""
        if self.current_mode == "live_view" and self.camera_manager.live_view_active:
            frame = self.camera_manager.get_next_live_frame()
            if frame:
                try:
                    # Convert JPEG to PIL Image
                    image = Image.open(io.BytesIO(frame.jpeg))
                    
                    # Resize window on first frame
                    if self.preview_manager.current_image_tk is None:
                        self.resize_window_for_image(image.width, image.height)
                    
                    # Display the image
                    self.preview_manager.display_image(image)
                except Exception as e:
                    print(f"Error processing live view frame: {str(e)}")
        
        # Schedule the next check
        self.window.after(25, self.check_live_view_updates)
    
    def shoot_key_pressed(self, event=None):
        """Handle the 'S' key press based on current mode."""
        if self.current_mode == "live_view":
            self.take_photo()
        elif self.current_mode == "preview":
            self.download_and_continue()
    
    def take_photo(self):
        """Take a photo and show the preview."""
        # Stop live view
        self.camera_manager.stop_live_view()
        self.update_status("Taking photo...")
        
        # Take the picture
        if self.camera_manager.take_picture():
            # Wait for camera to process the image
            time.sleep(2)
            
            # Show preview
            self.show_preview()
        else:
            self.update_status("Failed to take photo")
            # Restart live view if there was an error
            self.start_live_view()
    
    def show_preview(self):
        """Show a preview of the last taken photo."""
        self.update_status("Loading preview...")
        self.current_mode = "preview"
        
        # Get the latest image
        image_path, jpeg_data = self.camera_manager.get_latest_image()
        
        if image_path and jpeg_data:
            # Store image path for later download
            self.latest_image_path = image_path
            
            # Convert JPEG to PIL Image
            image = Image.open(io.BytesIO(jpeg_data))
            
            # Resize window based on image size
            self.resize_window_for_image(image.width, image.height)
            
            # Display the image
            self.preview_manager.display_image(image)
            
            # Update info
            self.update_status("Preview - S to accept and download, R to reject")
            self.info_label.config(text=f"Preview: {os.path.basename(image_path)}")
        else:
            self.update_status("Failed to load preview")
            # Restart live view
            self.start_live_view()
    
    def toggle_focus_peaking(self, event=None):
        """Toggle focus peaking feature."""
        if self.current_mode != "live_view":
            return
        
        if self.camera_manager.toggle_focus_peaking():
            status = "enabled" if self.camera_manager.focus_peaking_on else "disabled"
            self.update_status(f"Focus peaking {status}")
    
    def cycle_zoom(self, event=None):
        """Cycle through zoom levels."""
        if self.current_mode != "live_view":
            return
        
        success, zoom_level = self.camera_manager.cycle_zoom()
        if success:
            self.update_status(f"Zoom set to {zoom_level}x")
    
    def toggle_image_inversion(self, event=None):
        """Toggle image color inversion."""
        if self.current_mode != "preview":
            return
        
        if self.preview_manager.toggle_inversion():
            status = "inverted" if self.preview_manager.is_inverted else "restored"
            self.update_status(f"Image colors {status}")
    
    def reject_preview(self, event=None):
        """Reject the current preview and return to live view."""
        if self.current_mode != "preview":
            return
        
        self.update_status("Returning to live view...")
        self.start_live_view()
    
    def download_and_continue(self):
        """Download the current image and return to live view."""
        if self.current_mode != "preview" or not self.latest_image_path:
            return
        
        # Get the filename without path
        filename = os.path.basename(self.latest_image_path)
        
        # Determine file extension for output path
        is_raw = filename.lower().endswith('.orf')
        
        # For preview purposes, we still need the JPEG version
        if is_raw:
            display_msg = "Downloading RAW file..."
        else:
            display_msg = "Downloading JPEG file..."
            
        self.update_status(display_msg)
        
        # Download the image
        jpeg_data = self.camera_manager.download_image(self.latest_image_path)
        
        if jpeg_data:
            if is_raw:
                self.update_status("RAW file download complete. Saving...")
            # Save the image
            output_path = os.path.join(self.output_directory, filename)
            try:
                with open(output_path, "wb") as f:
                    f.write(jpeg_data)
                
                self.update_status(f"Image saved to {output_path}")
                print(f"{'RAW' if is_raw else 'JPEG'} image saved to {output_path}")
                
                # Return to live view
                time.sleep(1)  # Short pause to show the status message
                self.start_live_view()
            except Exception as e:
                self.update_status(f"Error saving image: {str(e)}")
                self.start_live_view()
        else:
            self.update_status("Failed to download image")
            self.start_live_view()