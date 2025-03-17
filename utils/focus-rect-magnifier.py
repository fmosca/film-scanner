#!/usr/bin/env python3
"""
Script to test setting a focus rectangle and then magnifying it
in the Olympus camera live view.

This implements the specific sequence:
1. Set focus rectangle
2. Set focus rectangle again to trigger magnification
"""
import time
import sys
import argparse
from olympuswifi.camera import OlympusCamera


def main():
    parser = argparse.ArgumentParser(description="Test focus rectangle and magnification")
    parser.add_argument("--x", type=int, default=50, help="X coordinate (0-100)")
    parser.add_argument("--y", type=int, default=50, help="Y coordinate (0-100)")
    parser.add_argument("--live-view", action="store_true", help="Start live view first")
    parser.add_argument("--steps", type=int, default=2, 
                       help="Number of times to set focus point (2 for standard magnify)")
    parser.add_argument("--delay", type=float, default=0.5, 
                       help="Delay between focus actions (seconds)")
    args = parser.parse_args()
    
    try:
        # Connect to camera
        print("Connecting to camera...")
        camera = OlympusCamera()
        print(f"Connected to {camera.get_camera_model()}")
        
        # Switch to recording mode
        print("Switching to recording mode...")
        camera.send_command('switch_cammode', mode='rec')
        
        # Start live view if requested
        if args.live_view:
            print("Starting live view...")
            camera.start_liveview(port=40000, lvqty="0640x0480")
            # Allow time for live view to establish
            time.sleep(1)
        
        # Normalize coordinates to valid range
        x = max(0, min(100, args.x))
        y = max(0, min(100, args.y))
        point_param = f"{x}:{y}"
        
        # Try different methods for setting focus point
        methods = [
            # Method 1: Use assignafframe to set focus point
            lambda: camera.send_command('exec_takemotion', com='assignafframe', point=point_param),
            
            # Method 2: Use takeready to prepare focus point
            lambda: camera.send_command('exec_takemotion', com='takeready', point=point_param),
            
            # Method 3: Try both in sequence (some cameras need this)
            lambda: (
                camera.send_command('exec_takemotion', com='assignafframe', point=point_param),
                time.sleep(0.2),
                camera.send_command('exec_takemotion', com='takeready', point=point_param)
            ),
            
            # Method 4: Additional try with MF assist function (if available)
            # This is camera specific and might need to be adjusted
            lambda: camera.set_camprop("MF_ASSIST", "ON") if "MF_ASSIST" in camera.get_settable_propnames_and_values() else None
        ]
        
        # Test setting focus points multiple times
        print(f"Setting focus point at ({x}, {y}) {args.steps} times...")
        
        # Try each method
        for method_idx, method in enumerate(methods):
            print(f"Trying method {method_idx + 1}...")
            try:
                # Execute each step the requested number of times
                for step in range(args.steps):
                    print(f"Step {step + 1}/{args.steps}...")
                    result = method()
                    # If the method returned a result and it wasn't successful, print it
                    if result and hasattr(result, 'status_code') and result.status_code != 200:
                        print(f"Warning: Status code {result.status_code}")
                    time.sleep(args.delay)
                
                # Try different magnification methods after setting focus point
                print("Attempting magnification controls...")
                
                # Method 1: Using ctrlzoom
                try:
                    print("Testing telemove magnification...")
                    camera.send_command('exec_takemisc', com='ctrlzoom', move='telemove')
                    time.sleep(2)  # Wait to see the effect
                    camera.send_command('exec_takemisc', com='ctrlzoom', move='off')
                except Exception as e:
                    print(f"telemove failed: {e}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Method {method_idx + 1} failed: {e}")
        
        # Some additional experiments with the manual focus assist feature
        try:
            print("\nTesting alternate magnification approaches...")
            
            # Try to check for manual focus assist (MF Mode or similar)
            all_props = camera.get_settable_propnames_and_values()
            
            # Look for MF related properties
            mf_props = [prop for prop in all_props.keys() if 'mf' in prop.lower()]
            
            if mf_props:
                print(f"Found MF-related properties: {mf_props}")
                for prop in mf_props:
                    print(f"Values for {prop}: {all_props[prop]}")
                    
                    # Try to enable any MF assist features
                    for value in all_props[prop]:
                        if 'on' in value.lower() or 'enabled' in value.lower():
                            try:
                                print(f"Setting {prop} to {value}...")
                                camera.set_camprop(prop, value)
                                time.sleep(2)  # Wait to see effect
                            except Exception as e:
                                print(f"Failed to set {prop} to {value}: {e}")
        except Exception as e:
            print(f"Error testing MF properties: {e}")
        
        # Clean up
        if args.live_view:
            print("Stopping live view...")
            camera.stop_liveview()
        
        print("Test complete")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
