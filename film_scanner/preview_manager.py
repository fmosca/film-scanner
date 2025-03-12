"""
Preview manager module for the Film Scanner application.
Handles displaying and manipulating preview images with improved performance.
"""
import io
import tkinter as tk
from PIL import Image, ImageTk
from .image_processor import ImageProcessor


class PreviewManager:
    """
    Manages the preview window and image display with optimized image handling.
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

        # Create image frame with black background
        self.image_frame = tk.Frame(parent, bg="black")
        self.image_frame.pack(side="top", fill="both", expand=True)

        self.image_label = tk.Label(self.image_frame, bg="black")
        self.image_label.pack(side="top", fill="both", expand=True)

        self.status_bar = status_bar
        self.info_frame = info_frame

        self.original_image = None
        self.current_image_tk = None
        self.is_inverted = False

        # Cached version of scaled image to avoid recomputing when toggling inversion
        self.scaled_image = None

        # Handle window resize events
        self.parent.bind("<Configure>", self.on_window_resize)
        self.resize_timer = None
        self.last_window_size = (0, 0)

    def on_window_resize(self, event):
        """Handle window resize events with debouncing to prevent excessive recomputation"""
        # Get current window size
        width = self.parent.winfo_width()
        height = self.parent.winfo_height()

        # Skip if window size hasn't meaningfully changed or is too small
        if (width <= 1 or height <= 1 or
                (abs(width - self.last_window_size[0]) < 10 and
                 abs(height - self.last_window_size[1]) < 10)):
            return

        # Save the current size
        self.last_window_size = (width, height)

        # Cancel any existing timer to prevent multiple rapid resizes
        if self.resize_timer is not None:
            self.parent.after_cancel(self.resize_timer)

        # Set new timer to update the image after a delay
        self.resize_timer = self.parent.after(150, self.update_image_after_resize)

    def update_image_after_resize(self):
        """Update the displayed image after a resize with proper dimensions"""
        if self.original_image:
            # Force re-scaling of the image
            self.scaled_image = None
            self.display_image(self.original_image, self.is_inverted, scale=True)

    def display_image(self, image, invert=False, scale=True):
        """
        Display an image in the preview area.

        Args:
            image: PIL.Image object or bytes of JPEG data
            invert: Whether to invert the image colors
            scale: Whether to scale the image to fit the window (True) or display at native resolution (False)

        Returns:
            bool: Success or failure
        """
        try:
            # Convert bytes to PIL.Image if needed
            if isinstance(image, bytes):
                image = Image.open(io.BytesIO(image))

            # Store original image
            self.original_image = image

            processed_image = None

            if scale:
                # Get window dimensions - add extra padding to prevent underestimation
                window_width = max(10, self.parent.winfo_width() - 20)  # More padding
                window_height = max(10, self.parent.winfo_height() -
                                    self.status_bar.winfo_height() -
                                    self.info_frame.winfo_height() - 20)  # More padding

                # Skip if window is too small
                if window_width <= 20 or window_height <= 20:
                    window_width = max(100, self.parent.winfo_reqwidth())
                    window_height = max(100, self.parent.winfo_reqheight())

                # Force scale to be recalculated
                self.scaled_image = None

                # Scale to fit
                self.scaled_image = ImageProcessor.scale_image_to_fit(
                    image, window_width, window_height)

                # Apply inversion if requested
                processed_image = ImageProcessor.invert_image(self.scaled_image) if invert else self.scaled_image
            else:
                # Display at native resolution without scaling
                processed_image = ImageProcessor.invert_image(image) if invert else image

            self.is_inverted = invert

            # Convert to PhotoImage and display
            self.current_image_tk = ImageTk.PhotoImage(processed_image)
            self.image_label.config(image=self.current_image_tk)

            # Force UI to update immediately - this is critical
            self.parent.update_idletasks()
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
        self.scaled_image = None
        self.is_inverted = False