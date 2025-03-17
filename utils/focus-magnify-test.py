#!/usr/bin/env python3
"""
Test script for exploring focus control and magnification features
of the Olympus E-M5 Mark III camera.
"""
import time
import sys
from olympuswifi.camera import OlympusCamera


class FocusMagnifyTester:
    """
    Test focus rectangle positioning and magnification features
    of Olympus cameras.
    """
    
    def __init__(self, verbose=True):
        """Initialize the tester with camera connection"""
        self.verbose = verbose
        self.camera = None
        self.connection_successful = False
        self.log("Initializing FocusMagnifyTester")
    
    def log(self, message):
        """Log messages if verbose mode is enabled"""
        if self.verbose:
            print(message)
    
    def connect(self):
        """Connect to the camera and verify recording mode"""
        try:
            self.log("Connecting to camera...")
            self.camera = OlympusCamera()
            model = self.camera.get_camera_model()
            self.log(f"Connected to {model}")
            self.connection_successful = True
            
            # Switch to recording mode
            self.log("Switching to recording mode...")
            self.camera.send_command('switch_cammode', mode='rec')
            
            # Start live view on port 40000
            self.log("Starting live view...")
            result = self.camera.start_liveview(port=40000, lvqty="0640x0480")
            self.log(f"Live view started: {result}")
            
            return True
        except Exception as e:
            print(f"Error connecting to camera: {e}")
            return False
    
    def test_focus_point(self, x, y):
        """
        Test setting focus point at (x,y)
        
        Args:
            x: X coordinate (0-100)
            y: Y coordinate (0-100)
        """
        try:
            # Ensure values are within range
            x = max(0, min(100, x))
            y = max(0, min(100, y))
            
            point_param = f"{x}:{y}"
            self.log(f"Setting focus point to {point_param}...")
            
            # First try assignafframe
            try:
                response = self.camera.send_command('exec_takemotion', com='assignafframe', point=point_param)
                self.log(f"Focus point set response: {response.status_code}")
            except Exception as e:
                self.log(f"Error setting focus point: {e}")
            
            # Wait a moment for the camera to process
            time.sleep(0.5)
            
            # Return success
            return True
        except Exception as e:
            print(f"Error setting focus point: {e}")
            return False
    
    def test_magnify(self, action):
        """
        Test magnification features
        
        Args:
            action: One of 'start', 'stop', 'in', 'out', 'move-left', 'move-right', 'move-up', 'move-down'
        """
        try:
            if action == 'start':
                # Try various magnification start methods
                # 1. First try ctrlzoom with telemove
                self.log("Starting magnification with telemove...")
                try:
                    response = self.camera.send_command('exec_takemisc', com='ctrlzoom', move='telemove')
                    self.log(f"Magnification start response: {response.status_code}")
                except Exception as e:
                    self.log(f"Error with telemove: {e}")
                
            elif action == 'stop':
                # Try to stop magnification
                self.log("Stopping magnification...")
                try:
                    response = self.camera.send_command('exec_takemisc', com='ctrlzoom', move='off')
                    self.log(f"Magnification stop response: {response.status_code}")
                except Exception as e:
                    self.log(f"Error stopping magnification: {e}")
                
            elif action == 'in':
                # Zoom in further
                self.log("Zooming in further...")
                try:
                    response = self.camera.send_command('exec_takemisc', com='ctrlzoom', move='telemove')
                    self.log(f"Zoom in response: {response.status_code}")
                except Exception as e:
                    self.log(f"Error zooming in: {e}")
                
            elif action == 'out':
                # Zoom out
                self.log("Zooming out...")
                try:
                    response = self.camera.send_command('exec_takemisc', com='ctrlzoom', move='widemove')
                    self.log(f"Zoom out response: {response.status_code}")
                except Exception as e:
                    self.log(f"Error zooming out: {e}")
            
            # Handle movement within a magnified view
            elif action.startswith('move-'):
                # We'd need to know how to move within a magnified view
                # This would be camera-specific
                self.log(f"Movement action {action} not yet implemented")
                
            else:
                self.log(f"Unknown magnification action: {action}")
                return False
                
            # Wait for camera to process
            time.sleep(0.5)
            return True
            
        except Exception as e:
            print(f"Error with magnification: {e}")
            return False
    
    def cleanup(self):
        """Clean up: stop live view and disconnect"""
        if not self.connection_successful:
            return
            
        try:
            # Turn off magnification if active
            self.test_magnify('stop')
            
            # Stop live view
            self.log("Stopping live view...")
            self.camera.stop_liveview()
            
            self.log("Test complete")
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main function to run the tests"""
    tester = FocusMagnifyTester()
    
    if not tester.connect():
        print("Failed to connect to camera")
        return 1
    
    try:
        # Allow some time for live view to start
        time.sleep(1)
        
        # Test focusing at different points
        points_to_test = [
            (50, 50),  # Center
            (25, 25),  # Top left
            (75, 25),  # Top right
            (25, 75),  # Bottom left
            (75, 75),  # Bottom right
        ]
        
        for x, y in points_to_test:
            print(f"\n--- Testing focus point ({x}, {y}) ---")
            tester.test_focus_point(x, y)
            # Wait to see the effect
            time.sleep(2)
        
        # Test magnification
        print("\n--- Testing magnification ---")
        tester.test_magnify('start')
        time.sleep(2)
        
        print("Zooming in more...")
        tester.test_magnify('in')
        time.sleep(2)
        
        print("Zooming out...")
        tester.test_magnify('out')
        time.sleep(2)
        
        print("Stopping magnification...")
        tester.test_magnify('stop')
        
        # Test focus point followed by magnification
        print("\n--- Testing focus point with immediate magnification ---")
        tester.test_focus_point(50, 50)  # Center
        time.sleep(1)
        tester.test_magnify('start')
        time.sleep(2)
        tester.test_magnify('stop')
        
    finally:
        # Always clean up
        tester.cleanup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
