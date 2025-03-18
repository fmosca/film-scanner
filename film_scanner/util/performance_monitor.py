"""
Performance monitor for the Film Scanner application.
Tracks performance metrics and provides reporting.
"""
import time
import collections
from typing import Tuple, Dict, List, Optional, Any


class PerformanceMonitor:
    """
    Monitors and reports on application performance.
    
    Tracks frame rates, processing times, and other performance
    metrics to help identify bottlenecks and ensure smooth operation.
    """
    
    def __init__(self, window_size: int = 10):
        """
        Initialize the performance monitor.
        
        Args:
            window_size: Number of seconds to consider for metrics
        """
        self.window_size = window_size
        self.frame_times = collections.deque(maxlen=100)
        self.error_times = collections.deque(maxlen=20)
        self.processing_times = collections.deque(maxlen=50)
        
        self.last_frame_time = 0
        self.last_status_message = ""
        
        # Track FPS
        self.fps_values = collections.deque(maxlen=10)
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Performance thresholds
        self.fps_warning_threshold = 10
        self.fps_critical_threshold = 5
        self.gap_warning_threshold = 0.5
        self.gap_critical_threshold = 1.0
        self.error_rate_warning_threshold = 0.2
        self.error_rate_critical_threshold = 0.5
    
    def record_frame(self, had_error: bool = False, processing_time: Optional[float] = None):
        """
        Record a frame attempt.
        
        Args:
            had_error: Whether the frame had an error
            processing_time: Time taken to process the frame (seconds)
        """
        current_time = time.time()
        
        # Only record if it's been at least 16ms (60fps max) since last frame
        if current_time - self.last_frame_time >= 0.016:
            self.frame_times.append(current_time)
            self.last_frame_time = current_time
            
            if had_error:
                self.error_times.append(current_time)
            
            if processing_time is not None:
                self.processing_times.append(processing_time)
            
            # Update frame count for FPS calculation
            self.frame_count += 1
            
            # Calculate FPS every second
            elapsed = current_time - self.last_fps_time
            if elapsed >= 1.0:
                self.current_fps = self.frame_count / elapsed
                self.fps_values.append(self.current_fps)
                self.frame_count = 0
                self.last_fps_time = current_time
    
    def get_fps(self) -> float:
        """
        Get the current frames per second.
        
        Returns:
            float: Current FPS
        """
        if len(self.fps_values) > 0:
            # Average of recent FPS calculations
            return sum(self.fps_values) / len(self.fps_values)
        return self.current_fps
    
    def get_health_status(self) -> Tuple[str, float, float, float]:
        """
        Get the current health status.
        
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
        if fps < self.fps_warning_threshold or error_rate > self.error_rate_warning_threshold or max_gap > self.gap_warning_threshold:
            status = "warning"
        if fps < self.fps_critical_threshold or error_rate > self.error_rate_critical_threshold or max_gap > self.gap_critical_threshold:
            status = "critical"
        
        return status, fps, error_rate, max_gap
    
    def get_processing_time_stats(self) -> Dict[str, float]:
        """
        Get statistics about frame processing times.
        
        Returns:
            dict: Processing time statistics
        """
        if not self.processing_times:
            return {"min": 0, "max": 0, "avg": 0}
        
        times = list(self.processing_times)
        return {
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times)
        }
    
    def get_status_message(self) -> str:
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
        if fps < self.fps_critical_threshold:
            message = f"{prefix} Low frame rate ({fps:.1f} FPS)"
        elif error_rate > self.error_rate_critical_threshold:
            message = f"{prefix} High error rate ({error_rate*100:.0f}%)"
        elif gap > self.gap_critical_threshold:
            message = f"{prefix} Frame gaps ({gap:.1f}s)"
        else:
            message = f"{prefix} Performance issues"
        
        # Cache and return
        self.last_status_message = message
        return message
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """
        Get a detailed performance report.
        
        Returns:
            dict: Detailed performance metrics
        """
        status, fps, error_rate, max_gap = self.get_health_status()
        processing_stats = self.get_processing_time_stats()
        
        return {
            "status": status,
            "fps": fps,
            "error_rate": error_rate,
            "max_gap": max_gap,
            "processing_time": processing_stats,
            "frame_count": len(self.frame_times),
            "error_count": len(self.error_times)
        }
    
    def reset(self) -> None:
        """Reset all performance metrics."""
        self.frame_times.clear()
        self.error_times.clear()
        self.processing_times.clear()
        self.fps_values.clear()
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        self.last_frame_time = 0
