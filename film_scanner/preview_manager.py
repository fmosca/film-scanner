"""
Preview manager module for the Film Scanner application.
Handles displaying and manipulating preview images.
"""
import io
import tkinter as tk
from PIL import Image, ImageTk
from .image_processor import ImageProcessor


class PreviewManager:
    """
    Manages the preview window and image display.
    """
    def __init__(self, parent, status_bar, info_frame):
        """
        Initialize the preview manager.
        
        Args:
            parent: Parent tkinter container
            status_bar: Status bar widget
            info_frame: Information frame widget
        """
        self.parent = parent
        self.image_label = tk.Label(parent, bg="black")
        self.image_label.pack(side="top", fill="both", expand=True)
        
        self.status_bar = status_bar
        self.info_frame = info_frame
        
        self.original_image = None
        self.current_image_tk = None
        self.is_inverted = False
    
    def display_image(self, image, invert=False):
        """
        Display an image in the preview area, scaled to fit.
        
        Args:
            image: PIL.Image object or bytes of JPEG data
            invert: Whether to invert the image colors
            
        Returns:
            bool: Success or failure
        """
        try:
            # Convert bytes to PIL.Image if needed
            if isinstance(image, bytes):
                image = Image.open(io.BytesIO(image))
            
            # Store original image
            self.original_image = image
            
            # Get window dimensions
            window_width = self.parent.winfo_width()
            window_height = self.parent.winfo_height() - self.status_bar.winfo_height() - self.info_frame.winfo_height()
            
            # Invert if requested
            processed_image = image
            if invert:
                processed_image = ImageProcessor.invert_image(image)
                self.is_inverted = True
            else:
                self.is_inverted = False
            
            # Scale to fit
            scaled_image = ImageProcessor.scale_image_to_fit(
                processed_image, window_width, window_height)
            
            # Convert to PhotoImage and display
            self.current_image_tk = ImageTk.PhotoImage(scaled_image)
            self.image_label.config(image=self.current_image_tk)
            
            return True
        except Exception as e:
            print(f"Error displaying image: {str(e)}")
            return False
    
    def toggle_inversion(self):
        """
        Toggle inversion of the currently displayed image.
        
        Returns:
            bool: Success or failure
        """
        if self.original_image is None:
            return False
        
        self.is_inverted = not self.is_inverted
        return self.display_image(self.original_image, self.is_inverted)
    
    def clear(self):
        """Clear the preview display."""
        self.image_label.config(image="")
        self.original_image = None
        self.current_image_tk = None
        self.is_inverted = False
