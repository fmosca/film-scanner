"""
Image processor module for the Film Scanner application.
Contains utility functions for image processing operations.
"""
import numpy as np
from PIL import Image


class ImageProcessor:
    """
    Responsible for processing operations on images.
    """
    @staticmethod
    def invert_image(image):
        """
        Invert the colors of an image.
        
        Args:
            image: PIL.Image object to invert
            
        Returns:
            PIL.Image: Inverted image
        """
        try:
            return Image.fromarray(255 - np.array(image))
        except Exception as e:
            print(f"Error inverting image: {str(e)}")
            return image
    
    @staticmethod
    def scale_image_to_fit(image, max_width, max_height):
        """
        Scale an image to fit within the specified dimensions while maintaining aspect ratio.
        
        Args:
            image: PIL.Image object to scale
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            PIL.Image: Scaled image
        """
        try:
            # Calculate scale to fit image in window
            scale_width = max_width / image.width
            scale_height = max_height / image.height
            scale = min(scale_width, scale_height)
            
            new_width = int(image.width * scale)
            new_height = int(image.height * scale)
            
            # Resize the image
            return image.resize((new_width, new_height), Image.LANCZOS)
        except Exception as e:
            print(f"Error scaling image: {str(e)}")
            return image
