"""
UI Manager for the Film Scanner application.
Handles all UI-related concerns including window creation,
layout management, and UI updates.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable, Dict, Tuple
import os

from ..control.state_manager import StateManager, AppState, StateChangeEvent
from ..camera.camera_status_bar import CameraStatusBar


class UIManager:
    """
    Manages all UI components and their interactions.
    
    Responsibilities:
    - Create and configure the main window
    - Manage UI layout and components
    - Handle UI updates based on state changes
    - Provide interface for updating UI elements
    """
    
    def __init__(self, 
                 root: tk.Tk, 
                 state_manager: StateManager, 
                 on_window_close: Callable[[], None]):
        """
        Initialize the UI manager.
        
        Args:
            root: Root tkinter window
            state_manager: Application state manager
            on_window_close: Callback for window close event
        """
        self.root = root
        self.state_manager = state_manager
        self.on_window_close = on_window_close
        
        # Window configuration
        self.root.title("Film Negative Scanner")
        self.root.protocol("WM_DELETE_WINDOW", self._handle_window_close)
        
        # Reference to key UI components
        self.status_bar = None
        self.info_frame = None
        self.image_frame = None
        self.camera_status_bar = None
        self.info_label = None
        self.quality_label = None
        self.fps_label = None
        self.health_label = None
        self.shortcut_label = None
        
        # UI state
        self.last_window_size = (0, 0)
        self.resize_timer = None
        self.show_fps = True
        
        # Subscribe to state changes
        self.state_manager.subscribe(self._handle_state_change)
        
        # Create UI components
        self._create_ui_components()
    
    def _create_ui_components(self):
        """Create all UI components and layout."""
        # Status bar at the very top
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.TOP, fill=tk.X)
        
        # Below status bar comes our main content area
        content_frame = tk.Frame(self.root)
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Image frame with black background takes most of the space
        self.image_frame = tk.Frame(content_frame, bg="black")
        self.image_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Camera status bar right below the image
        self.camera_status_bar = CameraStatusBar(self.root, height=30)
        
        # Information frame at the bottom
        self.info_frame = tk.Frame(self.root, height=50)
        self.info_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.info_label = tk.Label(self.info_frame, text="Initializing...", anchor=tk.W, padx=10)
        self.info_label.pack(side=tk.LEFT)
        
        self.quality_label = tk.Label(self.info_frame, text="", anchor=tk.W, padx=10)
        self.quality_label.pack(side=tk.LEFT)
        
        self.fps_label = tk.Label(self.info_frame, text="0 FPS", anchor=tk.W, padx=10)
        if self.show_fps:
            self.fps_label.pack(side=tk.LEFT)
        
        self.health_label = tk.Label(self.info_frame, text="", fg="red", anchor=tk.W, padx=10)
        self.health_label.pack(side=tk.LEFT)
        
        shortcut_text = "S: Shoot | F: Focus Peaking | P: Quality | I: Invert | ESC: Quit | ?: Help"
        self.shortcut_label = tk.Label(
            self.info_frame, 
            text=shortcut_text, 
            anchor=tk.E, 
            padx=10
        )
        self.shortcut_label.pack(side=tk.RIGHT)
    
    def _handle_window_close(self):
        """Handle window close event."""
        if self.on_window_close:
            self.on_window_close()
    
    def _handle_state_change(self, event: StateChangeEvent):
        """
        Handle application state changes.
        
        Args:
            event: State change event data
        """
        # Update UI based on new state
        if event.new_state == AppState.LIVE_VIEW:
            self.update_status("Live view active - Press S to take a photo")
            self.info_label.config(text="Live View")
            self.camera_status_bar.frame.pack(side=tk.TOP, fill=tk.X)
        
        elif event.new_state == AppState.TAKING_PHOTO:
            self.update_status("Taking photo...")
        
        elif event.new_state == AppState.LOADING_PREVIEW:
            self.update_status("Loading preview...")
        
        elif event.new_state == AppState.PREVIEW:
            self.update_status("Preview - S to accept and download, R to reject")
            self.info_label.config(text=f"Preview: {event.context.get('filename', '')}")
            self.camera_status_bar.frame.pack_forget()
        
        elif event.new_state == AppState.DOWNLOADING:
            self.update_status("Downloading image...")
        
        elif event.new_state == AppState.ERROR:
            error_message = event.context.get('error_message', 'An error occurred')
            self.update_status(f"Error: {error_message}")
        
        elif event.new_state == AppState.SHUTDOWN:
            self.update_status("Shutting down...")
    
    def update_status(self, message: str):
        """
        Update the status bar message.
        
        Args:
            message: Status message to display
        """
        self.status_bar.config(text=message)
        self.root.update_idletasks()  # Force GUI update
    
    def update_fps(self, fps: float):
        """
        Update the FPS display.
        
        Args:
            fps: Current frames per second
        """
        self.fps_label.config(text=f"{fps:.1f} FPS")
    
    def update_health_status(self, message: str, status: str = "ok"):
        """
        Update the health status display.
        
        Args:
            message: Health status message
            status: Status level ("ok", "warning", "critical")
        """
        self.health_label.config(text=message)
        
        # Set color based on status
        if status == "warning":
            self.health_label.config(fg="orange")
        elif status == "critical":
            self.health_label.config(fg="red")
        else:
            self.health_label.config(fg="black")
    
    def update_quality(self, quality: str):
        """
        Update the quality label.
        
        Args:
            quality: Current stream quality
        """
        self.quality_label.config(text=quality)
    
    def update_camera_status(self, aperture=None, shutter_speed=None, 
                             iso=None, exposure_warning=None, focus_status=None):
        """
        Update the camera status bar.
        
        Args:
            aperture: Aperture value
            shutter_speed: Shutter speed
            iso: ISO value
            exposure_warning: Exposure warning
            focus_status: Focus status
        """
        self.camera_status_bar.update(
            aperture=aperture,
            shutter_speed=shutter_speed,
            iso=iso,
            exposure_warning=exposure_warning,
            focus_status=focus_status
        )
    
    def get_image_frame(self) -> tk.Frame:
        """
        Get the image frame for displaying images.
        
        Returns:
            tk.Frame: Frame for image display
        """
        return self.image_frame
    
    def set_window_size(self, width: int, height: int, center: bool = True):
        """
        Set the window size.
        
        Args:
            width: Window width
            height: Window height
            center: Whether to center window on screen
        """
        self.root.geometry(f"{width}x{height}")
        
        if center:
            # Center the window on screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x_position = int((screen_width - width) / 2)
            y_position = int((screen_height - height) / 2)
            self.root.geometry(f"+{x_position}+{y_position}")
    
    def resize_for_image(self, width: int, height: int):
        """
        Resize window to fit an image with specified dimensions.
        
        Args:
            width: Image width
            height: Image height
        """
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate UI element heights
        status_bar_height = self.status_bar.winfo_reqheight()
        camera_status_height = self.camera_status_bar.height
        info_frame_height = self.info_frame.winfo_reqheight()
        
        # Total UI height
        ui_height = status_bar_height + camera_status_height + info_frame_height
        
        # Apply 5% margin to available screen space
        margin_percentage = 0.05
        available_width = int(screen_width * (1 - 2 * margin_percentage))
        available_height = int((screen_height - ui_height) * (1 - 2 * margin_percentage))
        
        # Calculate scaling
        width_ratio = available_width / width
        height_ratio = available_height / height
        
        # Use the smaller scaling to fit entirely on screen
        scale_factor = min(width_ratio, height_ratio)
        
        # Calculate new dimensions
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor) + ui_height
        
        # Set window size and center
        self.set_window_size(new_width, new_height)
    
    def set_initial_window_size(self, quality: str):
        """
        Set initial window size based on quality setting.
        
        Args:
            quality: Quality string like "0640x0480"
        """
        width, height = map(int, quality.split('x'))
        
        # Add some padding for UI elements
        ui_padding_height = 120  # Status bar + camera status bar + info frame
        
        # Set window size
        self.set_window_size(width, height + ui_padding_height)
    
    def show_message(self, title: str, message: str):
        """
        Show a message dialog.
        
        Args:
            title: Dialog title
            message: Message to display
        """
        tk.messagebox.showinfo(title, message)
    
    def show_error(self, title: str, message: str):
        """
        Show an error dialog.
        
        Args:
            title: Dialog title
            message: Error message to display
        """
        tk.messagebox.showerror(title, message)
    
    def show_confirmation(self, title: str, message: str) -> bool:
        """
        Show a confirmation dialog.
        
        Args:
            title: Dialog title
            message: Message to display
            
        Returns:
            bool: True if confirmed, False otherwise
        """
        return tk.messagebox.askyesno(title, message)
    
    def schedule_task(self, delay_ms: int, callback: Callable) -> str:
        """
        Schedule a task to run after a delay.
        
        Args:
            delay_ms: Delay in milliseconds
            callback: Function to call
            
        Returns:
            str: Timer ID for cancellation
        """
        return self.root.after(delay_ms, callback)
    
    def cancel_task(self, timer_id: str):
        """
        Cancel a scheduled task.
        
        Args:
            timer_id: Timer ID from schedule_task
        """
        self.root.after_cancel(timer_id)
    
    def force_update(self):
        """Force an immediate UI update."""
        self.root.update_idletasks()
        self.root.update()
