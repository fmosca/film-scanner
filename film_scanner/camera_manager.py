"""
Camera manager module for the Film Scanner application.
Handles all interactions with the Olympus camera.
"""
import queue
import threading
import io
import requests
from PIL import Image
from olympuswifi.camera import OlympusCamera
from olympuswifi.liveview import LiveViewReceiver


class CameraManager:
    """
    Responsible for all camera interactions, decoupled from UI.
    """

    def __init__(self, camera_cls=OlympusCamera):
        self.camera = camera_cls()
        self.live_view_active = False
        self.port = 40000
        self.img_queue = queue.SimpleQueue()
        self.receiver = None
        self.thread = None
        self.focus_peaking_on = False
        self.zoom_level = 1  # 1x zoom

        # Extend OlympusCamera functionality
        self._extend_camera_functionality()

    def _extend_camera_functionality(self):
        """Add additional functionality to the OlympusCamera class."""

        def send_command_with_direct_url(self, command, is_direct_url=False, **args):
            """Modified send_command that can handle direct URLs for RAW files."""
            if is_direct_url:
                # Direct URL access for raw files
                return requests.get(command, headers=self.HEADERS)
            return self._original_send_command(command, **args)

        self.camera._original_send_command = self.camera.send_command
        self.camera.send_command = send_command_with_direct_url.__get__(self.camera)

    def start_live_view(self, lvqty="0640x0480"):
        """Start the camera's live view streaming."""
        if self.live_view_active:
            return

        try:
            self.camera.start_liveview(port=self.port, lvqty=lvqty)

            # Start receiver in a new thread
            self.receiver = LiveViewReceiver(self.img_queue)
            self.thread = threading.Thread(target=self.receiver.receive_packets, args=[self.port])
            self.thread.daemon = True
            self.thread.start()

            self.live_view_active = True
            return True
        except Exception as e:
            print(f"Error starting live view: {str(e)}")
            return False

    def stop_live_view(self):
        """Stop the camera's live view streaming."""
        if not self.live_view_active:
            return True

        try:
            if self.receiver:
                self.receiver.shut_down()
            self.camera.stop_liveview()
            self.live_view_active = False
            return True
        except Exception as e:
            print(f"Error stopping live view: {str(e)}")
            return False

    def take_picture(self):
        """Take a picture with the camera."""
        try:
            # Reset zoom and focus peaking before taking the photo
            if self.zoom_level != 1 or self.focus_peaking_on:
                try:
                    self.camera.set_camprop("ZOOM_LEVEL", "1")
                    if self.focus_peaking_on:
                        self.camera.set_camprop("FOCUS_PEAKING", "OFF")
                except:
                    pass
                self.zoom_level = 1
                self.focus_peaking_on = False

            # Take the picture
            self.camera.take_picture()
            return True
        except Exception as e:
            print(f"Error taking picture: {str(e)}")
            return False

    def toggle_focus_peaking(self):
        """Toggle focus peaking feature on/off."""
        if not self.live_view_active:
            return False

        try:
            # Switch to recording mode if not already
            if self.camera.Mode != self.camera.CamMode.RECORD:
                self.camera.SwitchMode(self.camera.CamMode.RECORD)

            # Toggle focus peaking
            self.focus_peaking_on = not self.focus_peaking_on

            # Set the camera property for focus peaking
            if self.focus_peaking_on:
                self.camera.set_camprop("FOCUS_PEAKING", "ON")
            else:
                self.camera.set_camprop("FOCUS_PEAKING", "OFF")

            return True
        except Exception as e:
            print(f"Error toggling focus peaking: {str(e)}")
            return False

    def cycle_zoom(self):
        """Cycle through zoom levels: 1x, 3x, 5x, 7x, 10x."""
        if not self.live_view_active:
            return False, None

        try:
            # Switch to recording mode if not already
            if self.camera.Mode != self.camera.CamMode.RECORD:
                self.camera.SwitchMode(self.camera.CamMode.RECORD)

            # Cycle through zoom levels
            zoom_levels = [1, 3, 5, 7, 10]
            current_index = zoom_levels.index(self.zoom_level) if self.zoom_level in zoom_levels else 0
            next_index = (current_index + 1) % len(zoom_levels)
            self.zoom_level = zoom_levels[next_index]

            # Set the camera property for zoom
            self.camera.set_camprop("ZOOM_LEVEL", str(self.zoom_level))

            return True, self.zoom_level
        except Exception as e:
            print(f"Error changing zoom: {str(e)}")
            return False, None


    def get_latest_image(self, prefer_raw=True):
        """Get the most recent image from the camera. Set prefer_raw=False to always get JPEG."""
        try:
            # Try to switch to playback mode
            try:
                self.camera.send_command('switch_cammode', mode='play')
            except Exception as e:
                print(f"Warning: Could not switch to playback mode: {e}")

            # List images and find the last JPG image
            images = list(self.camera.list_images(dir='/DCIM/100OLYMP'))
            # First try to find matching RAW files
            raw_images = [img for img in images if img.file_name.lower().endswith('.orf')]
            jpg_images = [img for img in images if img.file_name.lower().endswith('.jpg')]

            if not raw_images and not jpg_images:
                raise Exception("No RAW or JPEG images found")

            # Select which image to return based on preference and availability
            if prefer_raw and raw_images:
                selected_image = raw_images[-1]
                print(f"Selected RAW image: {selected_image.file_name}")
            else:
                if not jpg_images:
                    raise Exception("No JPEG images found")
                selected_image = jpg_images[-1]
                print(f"Selected JPEG image: {selected_image.file_name}")

            # Define named download methods for better logging
            def download_full():
                return self.camera.download_image(selected_image.file_name)

            def download_screennail():
                return self.camera.download_screennail(selected_image.file_name)

            def download_thumbnail():
                return self.camera.download_thumbnail(selected_image.file_name)

            # Try each method until successful
            image_data = None
            download_methods = [download_full, download_screennail, download_thumbnail]

            for method in download_methods:
                try:
                    image_data = method()
                    print(f"Successfully downloaded image using {method.__name__}")
                    break
                except Exception as e:
                    print(f"Failed to download using {method.__name__}: {e}")

            if not image_data:
                raise Exception("Could not download image")

            return selected_image.file_name, image_data
        except Exception as e:
            print(f"Error getting latest image: {str(e)}")
            return None, None

    def download_image(self, image_path):
        """Download an image from the camera by its path."""
        try:
            # For RAW files, we need to use the direct HTTP GET request
            if image_path.lower().endswith('.orf'):
                url = f"{self.camera.URL_PREFIX}{image_path[1:]}"
                response = self.camera.send_command(url, is_direct_url=True)
                return response.content
            else:
                return self.camera.download_image(image_path)
        except Exception as e:
            print(f"Error downloading image {image_path}: {str(e)}")
            print(f"Trying alternative download method...")

            # Fallback method - try direct HTTP request for any file
            try:
                url = f"{self.camera.URL_PREFIX}{image_path[1:]}"
                response = self.camera.send_command(url, is_direct_url=True)
                return response.content
            except Exception as e2:
                print(f"Fallback download also failed: {str(e2)}")
                return None

    def get_next_live_frame(self):
        """Get the next frame from the live view queue."""
        if self.img_queue.empty():
            return None

        try:
            return self.img_queue.get()
        except Exception as e:
            print(f"Error getting live frame: {str(e)}")
            return None
