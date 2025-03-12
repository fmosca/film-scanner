"""
Frame Health Monitor for the Film Scanner application.
Monitors and reports on live view frame performance to ensure quality.
"""
import time
import collections


class FrameHealthMonitor:
    """
    Monitors frame rate and health of the live view stream.
    
    Tracks frame arrivals and errors to detect performance issues
    that might affect the camera status display and overall user experience.
    """
    
    def __init__(self, window_size=10):
        """
        Initialize the frame health monitor.
        
        Args:
            window_size: Number of seconds to consider for health metrics
        """
        self.window_size = window_size
        self.frame_times = collections.deque(maxlen=100)  # Store up to 100 frame times
        self.error_times = collections.deque(maxlen=20)   # Store up to 20 error times
        self.last_frame_time = 0
        self.last_status_message = ""
        
    def record_frame(self, had_error=False):
        """
        Record a frame attempt (successful or not).
        
        Args:
            had_error: Whether the frame had an error or not
        """
        current_time = time.time()
        
        # Only record if it's been at least 16ms (60fps) since last frame
        # This prevents recording duplicates from multiple UI refresh calls
        if current_time - self.last_frame_time >= 0.016:
            self.frame_times.append(current_time)
            self.last_frame_time = current_time
            
            if had_error:
                self.error_times.append(current_time)
    
    def get_health_status(self):
        """
        Get the current health status of the frame stream.
        
        Returns:
            tuple: (status, fps, error_rate, gap)
            - status: "ok", "warning", or "critical"
            - fps: Current frames per second
            - error_rate: Percentage of frames with errors
            - gap: Longest time between frames in seconds
        """
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Count frames in the window
        frames_in_window = sum(1 for t in self.frame_times if t >= window_start)
        errors_in_window = sum(1 for t in self.error_times if t >= window_start)
        
        # Calculate FPS
        fps = frames_in_window / self.window_size if frames_in_window > 0 else 0
        
        # Calculate error rate
        error_rate = errors_in_window / frames_in_window if frames_in_window > 0 else 0
        
        # Calculate largest gap between frames
        sorted_times = sorted([t for t in self.frame_times if t >= window_start])
        max_gap = 0
        
        if len(sorted_times) >= 2:
            gaps = [sorted_times[i] - sorted_times[i-1] for i in range(1, len(sorted_times))]
            max_gap = max(gaps) if gaps else 0
        
        # Determine status
        status = "ok"
        if fps < 10 or error_rate > 0.2 or max_gap > 0.5:
            status = "warning"
        if fps < 5 or error_rate > 0.5 or max_gap > 1.0:
            status = "critical"
            
        return status, fps, error_rate, max_gap
    
    def get_status_message(self):
        """
        Get a human-readable status message.
        
        Returns:
            str: Status message
        """
        status, fps, error_rate, gap = self.get_health_status()
        
        # Only show message if there's a problem
        if status == "ok":
            return ""
            
        # Format the error message
        if status == "warning":
            prefix = "Warning:"
        else:  # critical
            prefix = "Critical:"
            
        # Pick the most relevant issue to display
        if fps < 5:
            message = f"{prefix} Low frame rate ({fps:.1f} FPS)"
        elif error_rate > 0.5:
            message = f"{prefix} High error rate ({error_rate*100:.0f}%)"
        elif gap > 1.0:
            message = f"{prefix} Frame gaps ({gap:.1f}s)"
        else:
            message = f"{prefix} Performance issues"
            
        # Cache and return
        self.last_status_message = message
        return message