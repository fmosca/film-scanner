"""
Camera manager module for the Film Scanner application.
Handles all interactions with the Olympus camera with optimized live view.
"""
import queue
import threading
import io
import time
import random
import requests
from PIL import Image
from olympuswifi.camera import OlympusCamera
from olympuswifi.liveview import LiveViewReceiver


class CameraManager:
    """
    Responsible for all camera interactions, decoupled from UI.
    Optimized for faster live view performance.
    """

    def __init__(self, camera_cls=OlympusCamera):
        self.camera = camera_cls()
        self.live_view_active = False
        self.port = 40000
        self.img_queue = queue.Queue(maxsize=3)  # Limit queue size to prevent memory buildup
        self.receiver = None
        self.thread = None
        self.focus_peaking_on = False
        self.zoom_level = 1  # 1x zoom
        self.frame_processing_thread = None
        self.frame_processing_active = False
        self.processed_frame_queue = queue.Queue(maxsize=2)  # Queue for processed frames
        self.last_frame_time = 0
        self.frame_skip_count = 0
        self.current_lvqty = "0640x0480"  # Default quality

        # Extend OlympusCamera functionality
        self._extend_camera_functionality()

    def _extend_camera_functionality(self):
        """Add additional functionality to the OlympusCamera class."""

        def send_command_with_direct_url(self, command, is_direct_url=False, **args):
            """Modified send_command that can handle direct URLs for RAW files."""
            if is_direct_url:
                # Direct URL access for raw files
                return requests.get(command, headers=self.HEADERS, timeout=5)
            return self._original_send_command(command, **args)

        self.camera._original_send_command = self.camera.send_command
        self.camera.send_command = send_command_with_direct_url.__get__(self.camera)

    def start_live_view(self, lvqty="0640x0480"):
        """Start the camera's live view streaming with optimized frame handling."""
        if self.live_view_active:
            self.stop_live_view()  # Make sure to stop any existing live view
            time.sleep(0.5)  # Give time for resources to be released

        try:
            # Generate a random port number in the allowed range to avoid conflicts
            # This helps avoid the "Address already in use" error
            self.port = random.randint(40000, 50000)

            # Store the current quality setting
            self.current_lvqty = lvqty

            # Start live view with specified quality
            self.camera.start_liveview(port=self.port, lvqty=lvqty)

            # Start receiver in a new thread
            self.receiver = LiveViewReceiver(self.img_queue)
            self.thread = threading.Thread(target=self.receiver.receive_packets, args=[self.port])
            self.thread.daemon = True
            self.thread.start()

            # Start frame processing thread
            self.frame_processing_active = True
            self.frame_processing_thread = threading.Thread(target=self._process_frames)
            self.frame_processing_thread.daemon = True
            self.frame_processing_thread.start()

            self.live_view_active = True
            return True
        except Exception as e:
            print(f"Error starting live view: {str(e)}")
            return False

    def _process_frames(self):
        """Background thread to process frames from the camera."""
        while self.frame_processing_active:
            try:
                # Process every frame, don't skip any
                try:
                    frame = self.img_queue.get(timeout=0.05)
                except queue.Empty:
                    # No frames available, continue waiting
                    continue

                # Process the frame (convert to PIL Image)
                if frame and frame.jpeg:
                    try:
                        image = Image.open(io.BytesIO(frame.jpeg))

                        # If queue is full, make space
                        if self.processed_frame_queue.full():
                            try:
                                self.processed_frame_queue.get_nowait()
                            except queue.Empty:
                                pass

                        # Add to processed queue
                        self.processed_frame_queue.put(image)

                        # Update tracking stats
                        current_time = time.time()
                        self.last_frame_time = current_time
                    except Exception as e:
                        print(f"Error processing frame: {e}")

            except Exception as e:
                print(f"Error in frame processing loop: {str(e)}")
                time.sleep(0.1)  # Avoid spinning too fast on errors

    def stop_live_view(self):
        """Stop the camera's live view streaming."""
        if not self.live_view_active:
            return True

        try:
            # First stop the processing thread
            self.frame_processing_active = False
            if self.frame_processing_thread and self.frame_processing_thread.is_alive():
                self.frame_processing_thread.join(timeout=1.0)

            # Then stop the receiver
            if self.receiver:
                self.receiver.shut_down()
                self.receiver = None  # Clear the receiver reference

            # Clear thread
            self.thread = None

            # Clear all queues
            self._clear_queue(self.img_queue)
            self._clear_queue(self.processed_frame_queue)

            # Stop liveview on camera
            try:
                self.camera.stop_liveview()
            except Exception as e:
                print(f"Warning: Error while stopping camera liveview: {e}")

            # Mark as inactive
            self.live_view_active = False

            # Wait a moment to ensure all resources are released
            time.sleep(0.1)

            return True
        except Exception as e:
            print(f"Error stopping live view: {str(e)}")
            self.live_view_active = False  # Force it to false even on error
            return False

    def _clear_queue(self, q):
        """Safely clear a queue."""
        try:
            while not q.empty():
                q.get_nowait()
        except Exception:
            pass

    def take_picture(self):
        """Take a picture with the camera."""
        try:
            # Reset zoom and focus peaking before taking the photo
            if self.zoom_level != 1 or self.focus_peaking_on:
                try:
                    self.camera.set_camprop("ZOOM_LEVEL", "1")
                    if self.focus_peaking_on:
                        self.camera.set_camprop("FOCUS_PEAKING", "OFF")
                except Exception as e:
                    print(f"Warning: Could not reset zoom/focus peaking: {e}")
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

    def get_next_live_frame(self):
        """Get the next processed frame for display."""
        try:
            # Try to get a processed frame with minimal wait time
            # This is non-blocking to keep the UI responsive
            return self.processed_frame_queue.get_nowait() if not self.processed_frame_queue.empty() else None
        except Exception:
            return None

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

            # Always use screennail for preview for faster loading
            try:
                image_data = self.camera.download_screennail(selected_image.file_name)
                print(f"Successfully downloaded screennail preview")
                return selected_image.file_name, image_data
            except Exception as e:
                print(f"Failed to download screennail, falling back to alternatives: {e}")

                # Fall back to thumbnail if screennail fails
                try:
                    image_data = self.camera.download_thumbnail(selected_image.file_name)
                    print(f"Successfully downloaded thumbnail preview")
                    return selected_image.file_name, image_data
                except Exception as e:
                    print(f"Failed to download thumbnail, falling back to full image: {e}")

                    # Last resort, try full image
                    try:
                        image_data = self.camera.download_image(selected_image.file_name)
                        print(f"Successfully downloaded full image as preview")
                        return selected_image.file_name, image_data
                    except Exception as e:
                        print(f"Failed to download image: {e}")

            raise Exception("Could not download image preview")

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