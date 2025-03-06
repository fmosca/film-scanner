import unittest
from unittest.mock import MagicMock
from film_scanner.camera_manager import CameraManager
from vcr_config import my_vcr

class TestCameraManager(unittest.TestCase):
    def setUp(self):
        # Create a mock camera
        self.mock_camera = MagicMock()
        #self.camera_manager = CameraManager(self.mock_camera)
        self.camera_manager = CameraManager()

    def test_get_info(self):
        # Test getting camera info
        result = self.camera_manager.get_info()
        self.assertEqual(result, "Camera Info")

    @my_vcr.use_cassette('test_start_live_view')
    def test_start_live_view(self):
        # Test starting live view
        result = self.camera_manager.start_live_view()
        self.assertTrue(result)

    @my_vcr.use_cassette('test_take_picture')
    def test_take_picture(self):
        # Test taking a picture
        self.camera_manager.stop_live_view()
        result = self.camera_manager.take_picture()
        self.assertTrue(result)

    @my_vcr.use_cassette('test_get_latest_image')
    def test_get_latest_image(self):
        # Test getting the latest image
        file_name, jpeg_data = self.camera_manager.get_latest_image()
        self.assertIsNotNone(file_name)
        self.assertIsNotNone(jpeg_data)

if __name__ == '__main__':
    unittest.main()