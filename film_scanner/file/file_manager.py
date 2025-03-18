"""
File manager for the Film Scanner application.
Handles all file operations including saving, downloading, and directory management.
"""
import os
import threading
import shutil
from typing import Callable, Optional, Tuple
from datetime import datetime


class FileManager:
    """
    Manages all file operations for the application.
    
    Responsibilities:
    - Manage output directories
    - Handle image downloads
    - Save images to disk
    - Manage file naming
    """
    
    def __init__(self, output_directory: Optional[str] = None):
        """
        Initialize the file manager.
        
        Args:
            output_directory: Base directory for image storage
        """
        # Set default output directory if none provided
        if output_directory is None:
            self.output_directory = os.path.expanduser("~/Pictures/FilmScans")
        else:
            self.output_directory = output_directory
        
        # Create directory if it doesn't exist
        self._ensure_directory_exists(self.output_directory)
        
        # Active downloads tracking
        self._active_downloads = 0
        self._download_lock = threading.Lock()
        
    def _ensure_directory_exists(self, directory: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory: Directory path to check/create
            
        Returns:
            bool: True if directory exists or was created
        """
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                return True
            except Exception as e:
                print(f"Error creating directory {directory}: {e}")
                return False
        return True
    
    def get_output_directory(self) -> str:
        """
        Get the current output directory.
        
        Returns:
            str: Path to output directory
        """
        return self.output_directory
    
    def set_output_directory(self, directory: str) -> bool:
        """
        Set the output directory.
        
        Args:
            directory: New output directory
            
        Returns:
            bool: True if directory was set
        """
        if self._ensure_directory_exists(directory):
            self.output_directory = directory
            return True
        return False
    
    def create_dated_subdirectory(self) -> str:
        """
        Create a subdirectory with today's date.
        
        Returns:
            str: Path to created directory
        """
        today = datetime.now().strftime("%Y-%m-%d")
        subdir = os.path.join(self.output_directory, today)
        self._ensure_directory_exists(subdir)
        return subdir
    
    def save_image(self, image_data: bytes, filename: str, 
                   subdir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Save image data to a file.
        
        Args:
            image_data: Binary image data
            filename: Filename to save as
            subdir: Optional subdirectory within output directory
            
        Returns:
            tuple: (success, filepath)
        """
        try:
            # Determine output path
            if subdir:
                output_dir = os.path.join(self.output_directory, subdir)
                self._ensure_directory_exists(output_dir)
            else:
                output_dir = self.output_directory
            
            # Create full path
            filepath = os.path.join(output_dir, filename)
            
            # Write file
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            return True, filepath
        except Exception as e:
            print(f"Error saving image: {e}")
            return False, ""
    
    def download_image_async(self, 
                             download_func, 
                             image_path: str, 
                             on_complete: Callable[[bool, str, bytes], None]):
        """
        Download an image asynchronously.
        
        Args:
            download_func: Function to call to download image data
            image_path: Path of image on camera
            on_complete: Callback function for when download completes
                         Parameters: (success, image_path, image_data)
        """
        with self._download_lock:
            self._active_downloads += 1
        
        # Start download thread
        thread = threading.Thread(
            target=self._download_thread,
            args=(download_func, image_path, on_complete)
        )
        thread.daemon = True
        thread.start()
    
    def _download_thread(self, 
                         download_func, 
                         image_path: str, 
                         on_complete: Callable[[bool, str, bytes], None]):
        """
        Thread function for downloading image.
        
        Args:
            download_func: Function to call to download image data
            image_path: Path of image on camera
            on_complete: Callback function
        """
        try:
            # Call the provided download function
            image_data = download_func(image_path)
            
            if image_data:
                on_complete(True, image_path, image_data)
            else:
                on_complete(False, image_path, b"")
        except Exception as e:
            print(f"Error in download thread: {e}")
            on_complete(False, image_path, b"")
        finally:
            with self._download_lock:
                self._active_downloads -= 1
    
    def get_active_downloads(self) -> int:
        """
        Get the number of active downloads.
        
        Returns:
            int: Number of active downloads
        """
        with self._download_lock:
            return self._active_downloads
    
    def generate_filename(self, original_filename: str, prefix: str = "scan_") -> str:
        """
        Generate a filename based on the original filename.
        
        Args:
            original_filename: Original filename
            prefix: Prefix to add
            
        Returns:
            str: Generated filename
        """
        # Extract base filename without path
        base_filename = os.path.basename(original_filename)
        
        # Add timestamp if needed for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create new filename
        new_filename = f"{prefix}{timestamp}_{base_filename}"
        
        return new_filename