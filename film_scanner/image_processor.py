"""
Image processor module for the Film Scanner application.
Contains optimized utility functions for image processing operations.
"""
import numpy as np
from PIL import Image, ImageOps

class ImageProcessor:
    """
    Responsible for efficient processing operations on images.
    """
    
    # Cache for inverted images to avoid recalculation
    _inversion_cache = {}
    _cache_size_limit = 10  # Maximum number of images to cache
    
    @staticmethod
    def invert_image(image):
        """
        Invert the colors of an image with caching for performance.
        
        Args:
            image: PIL.Image object to invert
            
        Returns:
            PIL.Image: Inverted image
        """
        try:
            # Create a unique identifier for the image
            img_id = id(image)
            
            # Check if we already have this inverted in our cache
            if img_id in ImageProcessor._inversion_cache:
                return ImageProcessor._inversion_cache[img_id]
            
            # Use ImageOps for faster inversion than manual numpy operations
            inverted_image = ImageOps.invert(image.convert('RGB'))
            
            # Cache the result
            if len(ImageProcessor._inversion_cache) >= ImageProcessor._cache_size_limit:
                # Remove oldest item if cache is full
                ImageProcessor._inversion_cache.pop(next(iter(ImageProcessor._inversion_cache)))
            
            ImageProcessor._inversion_cache[img_id] = inverted_image
            return inverted_image
            
        except Exception as e:
            print(f"Error inverting image: {str(e)}")
            # Return original image on error
            return image
    
    @staticmethod
    def scale_image_to_fit(image, max_width, max_height):
        """
        Efficiently scale an image to fit within the specified dimensions 
        while maintaining aspect ratio.
        
        Args:
            image: PIL.Image object to scale
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            PIL.Image: Scaled image
        """
        try:
            # Calculate scale to fit image in window
            width, height = image.size
            
            # Don't scale if already smaller
            if width <= max_width and height <= max_height:
                return image
                
            scale_width = max_width / width
            scale_height = max_height / height
            scale = min(scale_width, scale_height)
            
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Use antialiasing only when downsampling by a significant amount
            # to improve performance without sacrificing much quality
            if scale < 0.5:
                resampling = Image.LANCZOS 
            elif scale <= 1.0:
                resampling = Image.BILINEAR
            else:
                resampling = Image.NEAREST
                
            # Resize the image
            return image.resize((new_width, new_height), resampling)
            
        except Exception as e:
            print(f"Error scaling image: {str(e)}")
            return image
            
    @staticmethod
    def clear_cache():
        """Clear the image processing caches to free memory"""
        ImageProcessor._inversion_cache.clear()
