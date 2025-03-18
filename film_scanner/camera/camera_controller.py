"""
Camera controller for the Film Scanner application.
Handles camera interactions and state management.
"""
import time
import queue
import threading
from typing import Optional, Callable, Dict, List, Tuple, Any

from ..control.state_manager import StateManager, AppState
from olympuswifi.camera import OlympusCamera


class CameraController:
    """
    Controls camera operations and manages camera state.
    
    This class serves as a facade over the lower-level camera interactions,
    providing higher-level operations like starting live view, taking photos,
    and downloading images.
    """
    
    def __init__(self, state_manager: StateManager, camera_cls=OlympusCamera):
        """
        Initialize the camera controller.
        
        Args:
            state_manager: Application state manager
            camera_cls: Camera class constructor (for dependency injection)
        """
        self.state_manager = state_manager
        self.camera = camera_cls()
        
        # Camera state
        self.live_view_active = False
        self.port = 40000
        self.focus_peaking_on = False
        self.zoom_level = 1  # 1x zoom
        self.current_lvqty = "0640x0480"  # Default quality
        self.current_camera_settings = {}
        
        # Image queues
        self.img_queue = queue.Queue(maxsize=3)
        self.status_queue = queue.Queue(maxsize=2)
        self.processed_frame_queue = queue.Queue(maxsize=2)
        
        # Threads
        self.receiver = None
        self.thread = None
        self.frame_processing_thread = None
        self.frame_processing_active = False
        
        # Performance tracking
        self.last_frame_time = 0
        self.frame_skip_count = 0
        
        # Live view qualities
        self.live_view_qualities = ["0320x0240", "0640x0480", "0800x0600", "1024x0768", "1280x0960"]
        
        # Camera modes
        self.camera_modes = ["rec", "play", "shutter"]
        
        # Register state transition handlers
        self._register_state_handlers()
        
        # Extend camera functionality
        self._extend_camera_functionality()
    
    def _register_state_handlers(self):
        """Register handlers for state transitions."""
        # Handle transition to live view
        self.state_manager.add_transition_handler(
            AppState.STARTUP, 
            AppState.LIVE_VIEW,
            self._handle_enter_live_view
        )
        
        self.state_manager.add_transition_handler(
            AppState.PREVIEW, 
            AppState.LIVE_VIEW,
            self._handle_enter_live_view
        )
        
        self.state_manager.add_transition_handler(
            AppState.ERROR, 
            AppState.LIVE_VIEW,
            self._handle_enter_live_view
        )
        
        # Handle exit from live view
        self.state_manager.add_transition_handler(
            AppState.LIVE_VIEW, 
            AppState.TAKING_PHOTO,
            self._handle_exit_live_view
        )
        
        self.state_manager.add_transition_handler(
            AppState.LIVE_VIEW, 
            AppState.SHUTDOWN,
            self._handle_exit_live_view
        )
        
        # Handle taking photo
        self.state_manager.add_transition_handler(
            AppState.TAKING_PHOTO, 
            AppState.LOADING_PREVIEW,
            self._handle_take_photo
        )
    
    def _extend_camera_functionality(self):
        """Add additional functionality to the OlympusCamera class."""
        # Define a function to add to the camera class
        def send_command_with_direct_url(self, command, is_direct_url=False, **args):
            """Modified send_command that can handle direct URLs for RAW files."""
            if is_direct_url:
                # Direct URL access for raw files
                import requests
                return requests.get(command, headers=self.HEADERS, timeout=5)
            return self._original_send_command(command, **args)
        
        # Store original method and attach new one
        self.camera._original_send_command = self.camera.send_command
        self.camera.send_command = send_command_with_direct_url.__get__(self.camera)
    
    def _handle_enter_live_view(self, event):
        """Handle transition to live view state."""
        # Start live view with current quality
        self.start_live_view(self.current_lvqty)
    
    def _handle_exit_live_view(self, event):
        """Handle transition from live view state."""
        # Stop live view
        self.stop_live_view()
    
    def _handle_take_photo(self, event):
        """Handle taking a photo."""
        # Take photo
        success = self.take_picture()
        
        # Wait for camera to process the image
        time.sleep(1.5)
        
        if success:
            # Successfully took photo, proceed to load preview
            self.state_manager.transition_to(AppState.LOADING_PREVIEW)
        else:
            # Failed to take photo, return to live view
            self.state_manager.transition_to(AppState.LIVE_VIEW)
    
    def start_live_view(self, lvqty="0640x0480"):
        """
        Start the camera's live view streaming.
        
        Args:
            lvqty: Live view quality setting
            
        Returns:
            bool: Success or failure
        """
        if self.live_view_active:
            self.stop_live_view()  # Stop any existing live view
            time.sleep(0.5)  # Give time for resources to be released
        
        try:
            import random
            # Generate a random port number to avoid conflicts
            self.port = random.randint(40000, 50000)
            
            # Store the current quality setting
            self.current_lvqty = lvqty
            
            # Start live view with specified quality
            self.camera.start_liveview(port=self.port, lvqty=lvqty)
            
            # Start receiver in a new thread
            from .extended_liveview_receiver import ExtendedLiveViewReceiver
            self.receiver = ExtendedLiveViewReceiver(self.img_queue, self.status_queue)
            self.thread = threading.Thread(target=self.receiver.receive_packets, args=[self.port])
            self.thread.daemon = True
            self.thread.start()
            
            # Start frame processing thread
            self.frame_processing_active = True
            self.frame_processing_thread = threading.Thread(target=self._process_frames)
            self.frame_processing_thread.daemon = True
            self.frame_processing_thread.start()
            
            # Start a status processing thread
            self.status_processing_thread = threading.Thread(target=self._process_status_updates)
            self.status_processing_thread.daemon = True
            self.status_processing_thread.start()
            
            self.live_view_active = True
            return True
        except Exception as e:
            print(f"Error starting live view: {str(e)}")
            return False
    
    def stop_live_view(self):
        """
        Stop the camera's live view streaming.
        
        Returns:
            bool: Success or failure
        """
        if not self.live_view_active:
            return True
        
        try:
            # Stop frame processing thread
            self.frame_processing_active = False
            if self.frame_processing_thread and self.frame_processing_thread.is_alive():
                self.frame_processing_thread.join(timeout=1.0)
            
            # Stop receiver
            if self.receiver:
                self.receiver.shut_down()
                self.receiver = None
            
            # Clear thread
            self.thread = None
            
            # Clear all queues
            self._clear_queue(self.img_queue)
            self._clear_queue(self.processed_frame_queue)
            self._clear_queue(self.status_queue)
            
            # Stop camera liveview
            try:
                self.camera.stop_liveview()
            except Exception as e:
                print(f"Warning: Error stopping camera liveview: {e}")
            
            # Mark as inactive
            self.live_view_active = False
            time.sleep(0.1)  # Ensure resources are released
            
            return True
        except Exception as e:
            print(f"Error stopping live view: {str(e)}")
            self.live_view_active = False  # Force to false even on error
            return False
    
    def _clear_queue(self, q):
        """
        Safely clear a queue.
        
        Args:
            q: Queue to clear
        """
        try:
            while not q.empty():
                q.get_nowait()
        except Exception:
            pass
    
    def _process_frames(self):
        """Background thread to process frames from the camera."""
        import io
        from PIL import Image
        
        while self.frame_processing_active:
            try:
                # Get frame from queue with timeout
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
                        self.last_frame_time = time.time()
                    except Exception as e:
                        print(f"Error processing frame: {e}")
            except Exception as e:
                print(f"Error in frame processing loop: {str(e)}")
                time.sleep(0.1)  # Avoid spinning too fast on errors
    
    def _process_status_updates(self):
        """Background thread to process camera status updates."""
        while self.live_view_active:
            try:
                # Get status updates if available
                try:
                    new_settings = self.status_queue.get(timeout=0.1)
                    if new_settings:
                        self.current_camera_settings.update(new_settings)
                except queue.Empty:
                    # No updates available, just continue
                    time.sleep(0.1)
                    continue
            except Exception as e:
                print(f"Error processing status updates: {str(e)}")
                time.sleep(0.1)  # Avoid tight loop on error
    
    def get_next_live_frame(self):
        """
        Get the next processed frame for display.
        
        Returns:
            PIL.Image: Next frame or None if no frame available
        """
        import io
        from PIL import Image
        
        try:
            # Try to get a processed frame without waiting
            if not self.processed_frame_queue.empty():
                frame = self.processed_frame_queue.get_nowait()
                # Convert to PIL Image if it's not already
                if not isinstance(frame, Image.Image) and hasattr(frame, 'jpeg'):
                    return Image.open(io.BytesIO(frame.jpeg))
                return frame
            return None
        except Exception:
            return None
    
    def take_picture(self):
        """
        Take a picture with the camera.
        
        Returns:
            bool: Success or failure
        """
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
        """
        Toggle focus peaking feature on/off.
        
        Returns:
            bool: Success or failure
        """
        if not self.live_view_active:
            return False
        
        try:
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
    
    def get_latest_camera_settings(self):
        """
        Get the latest camera settings.
        
        Returns:
            dict: Camera settings
        """
        if self.receiver:
            settings = self.receiver.get_latest_camera_settings()
            return settings
        return self.current_camera_settings
    
    def get_latest_image(self, prefer_raw=True):
        """
        Get the most recent image from the camera.
        
        Args:
            prefer_raw: Whether to prefer RAW files over JPEGs
            
        Returns:
            tuple: (filepath, image_data) or (None, None) on failure
        """
        try:
            # Try to switch to playback mode
            try:
                self.camera.send_command('switch_cammode', mode='play')
            except Exception as e:
                print(f"Warning: Could not switch to playback mode: {e}")
            
            # List images and find the last image
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
        """
        Download an image from the camera.
        
        Args:
            image_path: Path to image on camera
            
        Returns:
            bytes: Image data or None on failure
        """
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
    
    def get_live_view_qualities(self):
        """
        Get available live view quality settings.
        
        Returns:
            list: Available quality settings
        """
        return self.live_view_qualities
    
    def get_camera_modes(self):
        """
        Get available camera modes.
        
        Returns:
            list: Available camera modes
        """
        return self.camera_modes
    
    def switch_camera_mode(self, mode):
        """
        Switch the camera to a different mode.
        
        Args:
            mode: Camera mode
            
        Returns:
            bool: Success or failure
        """
        if mode not in self.camera_modes:
            return False
        
        try:
            result = self.camera.send_command('switch_cammode', mode=mode)
            return result is not None
        except Exception as e:
            print(f"Error switching camera mode: {e}")
            return False
