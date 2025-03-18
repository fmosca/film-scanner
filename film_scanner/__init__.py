"""
Film Scanner package for scanning film negatives using an Olympus camera.
"""

# Import main classes to simplify imports for users of the package
from .app import FilmScannerApp
from .camera.camera_controller import CameraController
from .preview.preview_manager import PreviewManager
from .util.performance_monitor import PerformanceMonitor

# Define version
__version__ = "0.2.0"
