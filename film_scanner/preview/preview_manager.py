"""
Preview manager for the Film Scanner application.
Handles displaying and manipulating preview images.
"""
import io
import tkinter as tk
from typing import Optional, Tuple
from PIL import Image, ImageTk


class PreviewManager:
    """
    Manages the preview window and image display.
    
    Handles image scaling, inversion, and display operations
    for both live view and preview modes.
    """
    
    def __init__(self, parent: tk.Frame, status_bar: tk.Label, info_frame: tk.Frame):
        """
        Initialize the preview manager.
        
        Args:
            parent: Parent frame for image display
            status_bar: Status bar for messages
            info_frame: Information frame at bottom of screen
        """
        self.parent = parent
        self.status_bar = status_bar
        self.info_frame = info_frame
        
        # Create image label for display
        self.image_label = tk.Label(self.parent, bg="black")
        self.image_label.pack(side="top", fill="both", expand=True)
        
        # State variables
        self.original_image = None
        self.current_image_tk = None
        self.is_inverted = False
        self.scaled_image = None
        
        # Window resize handling
        self.parent.bind("<Configure>", self.on_window_resize)
        self.resize_timer = None
        self.last_window_size = (0, 0)
    
    def on_window_resize(self, event):
        """
        Handle window resize events.
        
        Args:
            event: Window resize event
        """
        # Get current window size
        width = self.parent.winfo_width()
        height = self.parent.winfo_height()
        
        # Skip if the size hasn't meaningfully changed or is too small
        if (width <= 1 or height <= 1 or
                (abs(width - self.last_window_size[0]) < 10 and
                 abs(height - self.last_window_size[1]) < 10)):
            return
        
        # Save current size
        self.last_window_size = (width, height)
        
        # Cancel any existing timer
        if self.resize_timer is not None:
            self.parent.after_cancel(self.resize_timer)
        
        # Set new timer to update image after a delay
        self.resize_timer = self.parent.after(150, self.update_image_after_resize)
    
    def update_image_after_resize(self):
        """Update the displayed image after a resize."""
        if self.original_image:
            # Force re-scaling of the image
            self.scaled_image = None
            self.display_image(self.original_image, self.is_inverted, scale=True)
    
    def display_image(self, image, invert: bool = False, scale: bool = True) -> bool:
        """
        Display an image in the preview area.
        
        Args:
            image: PIL.Image object or bytes of JPEG data
            invert: Whether to invert image colors
            scale: Whether to scale image to fit window
            
        Returns:
            bool: Success or failure
        """
        try:
            # Convert bytes to PIL.Image if needed
            if isinstance(image, bytes):
                image = Image.open(io.BytesIO(image))
            
            # Store original image
            self.original_image = image
            
            if scale:
                # Get window dimensions
                window_width = max(10, self.parent.winfo_width() - 20)
                window_height = max(10, self.parent.winfo_height() - 20)
                
                # Skip if window is too small
                if window_width <= 20 or window_height <= 20:
                    window_width = max(100, self.parent.winfo_reqwidth())
                    window_height = max(100, self.parent.winfo_reqheight())
                
                # Scale to fit
                self.scaled_image = self._scale_image_to_fit(
                    image, window_width, window_height
                )
                
                # Apply inversion if requested
                processed_image = self._invert_image(self.scaled_image) if invert else self.scaled_image
            else:
                # Display at native resolution
                processed_image = self._invert_image(image) if invert else image
            
            # Store inversion state
            self.is_inverted = invert
            
            # Convert to PhotoImage and display
            self.current_image_tk = ImageTk.PhotoImage(processed_image)
            self.image_label.config(image=self.current_image_tk)
            
            # Force UI update
            self.parent.update_idletasks()
            return True
        except Exception as e:
            print(f"Error displaying image: {e}")
            return False
    
    def toggle_inversion(self) -> bool:
        """
        Toggle inversion of the displayed image.
        
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
        self.scaled_image = None
        self.is_inverted = False
    
    def _scale_image_to_fit(self, image: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """
        Scale an image to fit within specified dimensions.
        
        Args:
            image: PIL Image to scale
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            PIL.Image: Scaled image
        """
        # Get image dimensions
        width, height = image.size
        
        # No scaling needed if already smaller
        if width <= max_width and height <= max_height:
            return image
        
        # Calculate scaling factor
        scale_width = max_width / width
        scale_height = max_height / height
        scale = min(scale_width, scale_height)
        
        # Calculate new dimensions
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Choose appropriate resampling filter
        if scale < 0.5:
            # Use high quality for significant downsampling
            resampling = Image.LANCZOS
        elif scale <= 1.0:
            # Medium quality for minor downsampling
            resampling = Image.BILINEAR
        else:
            # Fast resampling for upscaling
            resampling = Image.NEAREST
        
        # Resize and return
        return image.resize((new_width, new_height), resampling)
    
    def _invert_image(self, image: Image.Image) -> Image.Image:
        """
        Invert the colors of an image.
        
        Args:
            image: PIL Image to invert
            
        Returns:
            PIL.Image: Inverted image
        """
        # Ensure image is in RGB mode for inversion
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Invert the image
        from PIL import ImageOps
        return ImageOps.invert(image)
    
    def get_image_size(self) -> Tuple[int, int]:
        """
        Get the size of the current image.
        
        Returns:
            tuple: (width, height) or (0, 0) if no image
        """
        if self.original_image:
            return self.original_image.size
        return (0, 0)
