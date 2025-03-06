import logging
import pytest
import sys
import os

from unittest.mock import MagicMock

from film_scanner.tests.vcr_config import my_vcr
from film_scanner.camera_manager import CameraManager

# Configure logging to output to stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)

logger = logging.getLogger(__name__)

# Create a fixture for determining if we should use live implementation
@pytest.fixture
def use_live():
    """Check if we should use the live implementation based on environment variable"""
    return os.environ.get("USE_LIVE_CAMERA") == "1"

# Create a fixture for the VCR context manager
@pytest.fixture
def vcr_test(request, use_live):
    module_name = request.module.__name__.split('.')[-1]
    function_name = request.function.__name__
    cassette_path = f"{module_name}/{function_name}"

    record_mode = 'all' if use_live else 'once'
    return my_vcr.use_cassette(path=cassette_path, record_mode=record_mode)


class TestCameraManager:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """
        Fixture to set up camera manager before each test
        autouse=True means it runs automatically for each test
        """
        # Create a mock camera
        self.mock_camera = MagicMock()
        # self.camera_manager = CameraManager(self.mock_camera)
        self.camera_manager = CameraManager()

    def test_start_live_view(self, vcr_test):
        """Test starting live view"""
        with vcr_test:
            logger.debug("Starting test_start_live_view")
            result = self.camera_manager.start_live_view()
            logger.debug(f"Start live view result: {result}")
            assert result is True

    def test_take_picture(self, vcr_test):
        """Test taking a picture"""
        with vcr_test:
            logger.debug("Starting test_take_picture")
            self.camera_manager.stop_live_view()
            result = self.camera_manager.take_picture()
            logger.debug(f"Take picture result: {result}")
            assert result is True

    def test_get_latest_image(self, vcr_test):
        """Test getting the latest image"""
        with vcr_test:
            logger.debug("Starting test_get_latest_image")
            file_name, jpeg_data = self.camera_manager.get_latest_image()
            logger.debug(f"Get latest image result - filename: {file_name}")
            assert file_name is not None
            assert jpeg_data is not None