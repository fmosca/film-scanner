"""
Main application coordinator for the Film Scanner application.
Initializes and connects all components.
"""
import os
import tkinter as tk
import time
import io
from PIL import Image, ImageTk
from typing import Optional, Dict, Any

from .control.state_manager import StateManager, AppState
from .control.keyboard_controller import KeyboardController
from .ui.ui_manager import UIManager
from .camera.camera_controller import CameraController
from .file.file_manager import FileManager
from .preview.preview_manager import PreviewManager
from .util.performance_monitor import PerformanceMonitor
from .util.settings_manager import SettingsManager


class FilmScannerApp:
    """
    Main application coordinator for the Film Scanner App.
    
    Coordinates between components and handles high-level workflows.
    """
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the application.
        
        Args:
            root: Root tkinter window
        """
        # Create core components
        self.state_manager = StateManager(AppState.STARTUP)
        self.settings_manager = SettingsManager()
        self.ui_manager = UIManager(root, self.state_manager, self.on_window_close)
        self.camera_controller = CameraController(self.state_manager)
        self.file_manager = FileManager(self.settings_manager.get_output_directory())
        self.preview_manager = PreviewManager(
            self.ui_manager.get_image_frame(),
            self.ui_manager.status_bar, 
            self.ui_manager.info_frame
        )
        self.keyboard_controller = KeyboardController(root, self.state_manager)
        self.performance_monitor = PerformanceMonitor()
        
        # UI update timers
        self.frame_update_timer = None
        self.health_check_timer = None
        self.camera_settings_timer = None
        
        # State variables
        self.current_quality_index = self.settings_manager.get("quality_index", 1)
        self.latest_image_path = None
        self.frame_count = 0
        self.last_fps_check_time = time.time()
        self.fps = 0
        
        # Register keyboard commands
        self._register_keyboard_commands()
        
        # Set initial window size
        qualities = self.camera_controller.get_live_view_qualities()
        self.ui_manager.set_initial_window_size(qualities[self.current_quality_index])
        self.ui_manager.update_quality(qualities[self.current_quality_index])
        
        # Apply UI settings
        self._apply_ui_settings()
        
        # Show instructions
        self.show_instructions()
        
        # Start checking for frame updates
        self.frame_update_timer = self.ui_manager.schedule_task(16, self.check_live_view_updates)
        
        # Start health monitoring
        self.health_check_timer = self.ui_manager.schedule_task(1000, self.update_health_status)
        
        # Start camera settings updates
        self.camera_settings_timer = self.ui_manager.schedule_task(200, self.update_camera_settings)
        
        # Load settings
        self._apply_settings()
        
        # Transition to live view state
        self.state_manager.transition_to(AppState.LIVE_VIEW)
    
    def _register_keyboard_commands(self):
        """Register keyboard commands with the controller."""
        # Global commands (work in any state)
        self.keyboard_controller.register_command("<Escape>", self.on_window_close)
        self.keyboard_controller.register_command("h", self.show_instructions)
        self.keyboard_controller.register_command("?", self.show_instructions)
        
        # Live view state commands
        self.keyboard_controller.register_state_commands(
            AppState.LIVE_VIEW,
            {
                "s": self.take_photo,
                "f": self.toggle_focus_peaking,
                "p": self.cycle_live_view_quality,
                "1": lambda: self.switch_camera_mode("rec"),
                "2": lambda: self.switch_camera_mode("play"),
                "3": lambda: self.switch_camera_mode("shutter"),
                "d": self.toggle_debug_info,
                "z": self.toggle_zoom_level
            }
        )
        
        # Preview state commands
        self.keyboard_controller.register_state_commands(
            AppState.PREVIEW,
            {
                "s": self.download_and_continue,
                "r": self.reject_preview,
                "i": self.toggle_image_inversion
            }
        )
    
    def _apply_settings(self):
        """Apply settings from the settings manager."""
        # Set output directory
        output_dir = self.settings_manager.get_output_directory()
        self.file_manager.set_output_directory(output_dir)
        
        # Set quality
        quality_index = self.settings_manager.get("quality_index", 1)
        if quality_index != self.current_quality_index:
            self.current_quality_index = quality_index
            qualities = self.camera_controller.get_live_view_qualities()
            self.camera_controller.current_lvqty = qualities[self.current_quality_index]
    
    def _apply_ui_settings(self):
        """Apply UI-specific settings."""
        # Show FPS counter if enabled
        show_fps = self.settings_manager.get("show_fps", True)
        if show_fps != self.ui_manager.show_fps:
            self.ui_manager.show_fps = show_fps
            if show_fps:
                self.ui_manager.fps_label.pack(side=tk.LEFT)
            else:
                self.ui_manager.fps_label.pack_forget()
    
    def on_window_close(self):
        """Handle window close event."""
        try:
            # Save settings
            self.settings_manager.set("quality_index", self.current_quality_index)
            self.settings_manager.save_settings()
            
            # Cancel any pending timers
            if self.frame_update_timer:
                self.ui_manager.cancel_task(self.frame_update_timer)
            if self.health_check_timer:
                self.ui_manager.cancel_task(self.health_check_timer)
            if self.camera_settings_timer:
                self.ui_manager.cancel_task(self.camera_settings_timer)
            
            # Stop camera
            self.camera_controller.stop_live_view()
            
            # Transition to shutdown state
            self.state_manager.transition_to(AppState.SHUTDOWN)
            
            # Close window
            self.ui_manager.root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")
    
    def show_instructions(self):
        """Show application instructions."""
        instructions = """
        Film Negative Scanner - Keyboard Controls
        
        S         - Take photo when in live view / Accept and download when in preview
        F         - Toggle focus peaking
        Z         - Toggle zoom level
        P         - Cycle through live view quality settings
        ESCAPE    - Quit the application
        R         - Reject preview and return to live view
        I         - Invert image colors (helpful for negative film)
        H or ?    - Show this help
        1/2/3     - Switch camera modes (rec/play/shutter)
        D         - Show debug information
        """
        self.ui_manager.update_status("Ready - Press S to take a photo")
        self.ui_manager.show_message("Instructions", instructions)
    
    def check_live_view_updates(self):
        """Check for new frames and update the display."""
        try:
            if self.state_manager.current_state == AppState.LIVE_VIEW and self.camera_controller.live_view_active:
                start_time = time.time()
                frame = self.camera_controller.get_next_live_frame()
                
                # Record a frame attempt
                had_error = False
                
                if frame:
                    try:
                        # Display the frame without scaling (at native resolution)
                        self.preview_manager.display_image(frame, self.preview_manager.is_inverted, scale=False)
                        
                        # Force UI update
                        self.ui_manager.force_update()
                        
                        # Update frame counter and FPS display
                        self.frame_count += 1
                        self._update_fps_display()
                        
                    except Exception as e:
                        had_error = True
                        print(f"Error displaying frame: {e}")
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Record performance metrics
                self.performance_monitor.record_frame(had_error=had_error, processing_time=processing_time)
            
            # Schedule next check
            self.frame_update_timer = self.ui_manager.schedule_task(16, self.check_live_view_updates)
            
        except Exception as e:
            print(f"Error in check_live_view_updates: {e}")
            # Ensure we keep checking even if there's an error
            self.frame_update_timer = self.ui_manager.schedule_task(100, self.check_live_view_updates)
    
    def _update_fps_display(self):
        """Update the FPS counter display."""
        current_time = time.time()
        elapsed = current_time - self.last_fps_check_time
        
        # Update FPS calculation every second
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.ui_manager.update_fps(self.fps)
            self.frame_count = 0
            self.last_fps_check_time = current_time
    
    def update_health_status(self):
        """Update the health status display."""
        if self.state_manager.current_state == AppState.LIVE_VIEW:
            # Get current health status
            status, fps, error_rate, gap = self.performance_monitor.get_health_status()
            message = self.performance_monitor.get_status_message()
            
            # Update UI with health status
            self.ui_manager.update_health_status(message, status)
        
        # Schedule next update
        self.health_check_timer = self.ui_manager.schedule_task(1000, self.update_health_status)
    
    def update_camera_settings(self):
        """Update camera status display with current settings."""
        try:
            if self.state_manager.current_state == AppState.LIVE_VIEW and self.camera_controller.live_view_active:
                # Get latest camera settings
                settings = self.camera_controller.get_latest_camera_settings()
                
                # Update UI with camera settings
                self.ui_manager.update_camera_status(
                    aperture=settings.get('aperture'),
                    shutter_speed=settings.get('shutter_speed'),
                    iso=settings.get('iso'),
                    exposure_warning=settings.get('exposure_compensation'),
                    focus_status=settings.get('focus_status')
                )
        except Exception as e:
            print(f"Error updating camera settings: {e}")
        
        # Schedule next update
        self.camera_settings_timer = self.ui_manager.schedule_task(200, self.update_camera_settings)
    
    def take_photo(self):
        """Initiate photo capture process."""
        # Transition to taking photo state
        self.state_manager.transition_to(AppState.TAKING_PHOTO)
    
    def show_preview(self, image_path, image_data):
        """
        Show a preview of a captured image.
        
        Args:
            image_path: Path to the image
            image_data: Raw image data
        """
        try:
            # Store image path for later download
            self.latest_image_path = image_path
            
            # Convert image data to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Resize window to fit image
            self.ui_manager.resize_for_image(image.width, image.height)
            
            # Display the image (with scaling for preview)
            self.preview_manager.display_image(image, scale=True)
            
            # Update state context with filename
            filename = os.path.basename(image_path)
            self.state_manager.transition_to(AppState.PREVIEW, {"filename": filename})
            
            return True
        except Exception as e:
            print(f"Error showing preview: {e}")
            self.state_manager.transition_to(AppState.ERROR, {"error_message": str(e)})
            return False
    
    def toggle_focus_peaking(self):
        """Toggle focus peaking feature."""
        if self.state_manager.current_state != AppState.LIVE_VIEW:
            return
        
        if self.camera_controller.toggle_focus_peaking():
            status = "enabled" if self.camera_controller.focus_peaking_on else "disabled"
            self.ui_manager.update_status(f"Focus peaking {status}")
    
    def toggle_zoom_level(self):
        """Toggle camera zoom level."""
        if self.state_manager.current_state != AppState.LIVE_VIEW:
            return
        
        # This would need implementation in the camera controller
        self.ui_manager.update_status("Zoom feature not implemented yet")
    
    def cycle_live_view_quality(self):
        """Cycle through available live view quality settings."""
        if self.state_manager.current_state != AppState.LIVE_VIEW:
            return
        
        # Stop live view
        self.camera_controller.stop_live_view()
        
        # Cycle to next quality
        qualities = self.camera_controller.get_live_view_qualities()
        self.current_quality_index = (self.current_quality_index + 1) % len(qualities)
        new_quality = qualities[self.current_quality_index]
        
        # Update settings
        self.settings_manager.set("quality_index", self.current_quality_index)
        
        # Update UI
        self.ui_manager.update_quality(new_quality)
        self.ui_manager.set_initial_window_size(new_quality)
        self.ui_manager.update_status(f"Changing live view quality to {new_quality}...")
        
        # Reset performance monitor
        self.performance_monitor.reset()
        
        # Restart live view with new quality
        self.camera_controller.start_live_view(lvqty=new_quality)
    
    def toggle_image_inversion(self):
        """Toggle image color inversion in preview mode."""
        if self.state_manager.current_state != AppState.PREVIEW:
            return
        
        if self.preview_manager.toggle_inversion():
            status = "inverted" if self.preview_manager.is_inverted else "restored"
            self.ui_manager.update_status(f"Image colors {status}")
    
    def reject_preview(self):
        """Reject current preview and return to live view."""
        if self.state_manager.current_state != AppState.PREVIEW:
            return
        
        self.state_manager.transition_to(AppState.LIVE_VIEW)
    
    def download_and_continue(self):
        """Download current image and return to live view."""
        if self.state_manager.current_state != AppState.PREVIEW or not self.latest_image_path:
            return
        
        # Transition to downloading state
        self.state_manager.transition_to(AppState.DOWNLOADING)
        
        # Get filename
        filename = os.path.basename(self.latest_image_path)
        
        # Start download process
        self.file_manager.download_image_async(
            self.camera_controller.download_image,
            self.latest_image_path,
            self._on_download_complete
        )
    
    def _on_download_complete(self, success, image_path, image_data):
        """
        Callback for when download completes.
        
        Args:
            success: Whether download was successful
            image_path: Path to the image
            image_data: Image data
        """
        if success:
            # Save the image
            filename = os.path.basename(image_path)
            use_dated_subdirs = self.settings_manager.get("create_dated_subdirectories", True)
            
            if use_dated_subdirs:
                subdir = time.strftime("%Y-%m-%d")
            else:
                subdir = None
            
            success, filepath = self.file_manager.save_image(image_data, filename, subdir)
            
            if success:
                self.ui_manager.update_status(f"Image saved to {filepath}")
                # Wait briefly, then return to live view
                self.ui_manager.schedule_task(1000, lambda: self.state_manager.transition_to(AppState.LIVE_VIEW))
            else:
                self.state_manager.transition_to(AppState.ERROR, {"error_message": "Failed to save image"})
        else:
            self.state_manager.transition_to(AppState.ERROR, {"error_message": "Failed to download image"})
    
    def switch_camera_mode(self, mode):
        """
        Switch the camera to a different mode.
        
        Args:
            mode: Camera mode
        """
        if mode not in self.camera_controller.get_camera_modes():
            return
        
        # Stop live view if active
        was_live_view_active = self.camera_controller.live_view_active
        if was_live_view_active:
            self.camera_controller.stop_live_view()
        
        self.ui_manager.update_status(f"Switching to {mode} mode...")
        
        # Switch mode
        if self.camera_controller.switch_camera_mode(mode):
            self.ui_manager.update_status(f"Camera is now in {mode} mode")
            
            # If we switched to rec mode and were in live view, restart it
            if mode == "rec" and was_live_view_active:
                qualities = self.camera_controller.get_live_view_qualities()
                self.camera_controller.start_live_view(lvqty=qualities[self.current_quality_index])
        else:
            self.ui_manager.update_status(f"Failed to switch to {mode} mode")
            # Restart live view if it was active
            if was_live_view_active:
                qualities = self.camera_controller.get_live_view_qualities()
                self.camera_controller.start_live_view(lvqty=qualities[self.current_quality_index])
    
    def toggle_debug_info(self):
        """Toggle display of debug information."""
        if self.state_manager.current_state != AppState.LIVE_VIEW:
            return
        
        try:
            # Get performance report
            perf_report = self.performance_monitor.get_detailed_report()
            
            # Get camera settings
            cam_settings = self.camera_controller.get_latest_camera_settings()
            
            # Print debug info
            print("--- Debug Information ---")
            print(f"Performance: {perf_report}")
            print(f"Camera Settings: {cam_settings}")
            print("------------------------")
            
            self.ui_manager.update_status("Debug info printed to console")
        except Exception as e:
            print(f"Error getting debug info: {e}")
