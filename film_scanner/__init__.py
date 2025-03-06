"""
Film Scanner package for scanning film negatives using an Olympus camera.
"""

# Import main classes to simplify imports for users of the package
from .film_scanner_app import FilmScannerApp
from .camera_manager import CameraManager
from .preview_manager import PreviewManager
from .image_processor import ImageProcessor

# Define version
__version__ = "0.1.0"
