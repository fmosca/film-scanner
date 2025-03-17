#!/usr/bin/env python3
"""
Debug script for exploring focus control with error 1004 handling.
"""
import time
import sys
from olympuswifi.camera import OlympusCamera, RequestError, ResultError


def main():
    try:
        print("Connecting to camera...")
        camera = OlympusCamera()
        print(f"Connected to {camera.get_camera_model()}")
        
        # Check camera mode and switch to rec mode
        print("Switching to recording mode...")
        camera.send_command('switch_cammode', mode='rec', lvqty="0640x0480")
        time.sleep(1)  # Give camera time to switch
        
        # Start live view
        print("Starting live view...")
        result = camera.start_liveview(port=40000, lvqty="0640x0480")
        print(f"Live view started with functions: {result}")
        time.sleep(1)  # Give live view time to start
        
        # First test: Simple focus point setting
        print("\n--- Testing focus point setting ---")
        try:
            point = "50:50"  # Center
            print(f"Setting focus point to {point}...")
            response = camera.send_command('exec_takemotion', com='assignafframe', point=point)
            print(f"Response: {response.status_code}")
            print(f"Headers: {response.headers}")
            print(f"Content: {response.text[:100]}")  # Show first 100 chars
            time.sleep(1)
        except Exception as e:
            print(f"Error setting focus point: {e}")
        
        # Second test: Try to double-tap focus point for magnification
        print("\n--- Testing double focus point setting ---")
        try:
            point = "50:50"  # Center
            print(f"Setting focus point to {point} twice...")
            
            # First tap
            response = camera.send_command('exec_takemotion', com='assignafframe', point=point)
            print(f"First tap response: {response.status_code}")
            time.sleep(0.5)
            
            # Second tap on same point
            response = camera.send_command('exec_takemotion', com='assignafframe', point=point)
            print(f"Second tap response: {response.status_code}")
            time.sleep(3)  # Wait to see if magnification occurs
        except Exception as e:
            print(f"Error with double focus point: {e}")
        
        # Third test: Try takemisc with all parameters
        print("\n--- Testing ctrlzoom with full parameters ---")
        try:
            # Look up available parameters for ctrlzoom
            cmd_desc = camera.commands['exec_takemisc']
            if cmd_desc.args and 'com' in cmd_desc.args:
                if 'ctrlzoom' in cmd_desc.args['com']:
                    print(f"ctrlzoom parameters: {cmd_desc.args['com']['ctrlzoom']}")
            
            # Try with move parameter   
            print("Trying 'exec_takemisc' with 'ctrlzoom'...")
            
            # Try with different moves
            moves = ['telemove', 'widemove', 'off', 'wideterm', 'teleterm']
            for move in moves:
                try:
                    print(f"Testing move='{move}'...")
                    response = camera.send_command('exec_takemisc', com='ctrlzoom', move=move)
                    print(f"Response for {move}: {response.status_code}")
                    time.sleep(1)
                except Exception as e:
                    error_str = str(e)
                    if "1004" in error_str:
                        print(f"Error 1004 (missing parameter) for {move}")
                        # Try to analyze what parameter might be missing
                        print(f"We sent: com=ctrlzoom, move={move}")
                    else:
                        print(f"Error with {move}: {e}")
        except Exception as e:
            print(f"Error with ctrlzoom test: {e}")
        
        # Fourth test: Explore MF assist features
        print("\n--- Checking for MF assist features ---")
        try:
            properties = camera.get_settable_propnames_and_values()
            for prop_name in properties.keys():
                if 'mf' in prop_name.lower() or 'magnif' in prop_name.lower() or 'assist' in prop_name.lower() or 'zoom' in prop_name.lower():
                    print(f"Found property: {prop_name} = {properties[prop_name]}")
                    try:
                        # Get current value
                        current = camera.get_camprop(prop_name)
                        print(f"Current value: {current}")
                    except:
                        print("Could not get current value")
        except Exception as e:
            print(f"Error checking properties: {e}")
        
        # Fifth test: Manual focus point on then off to try to trigger magnification
        print("\n--- Testing MF point assignment then release ---")
        try:
            # Assign focus point
            response = camera.send_command('exec_takemotion', com='assignafframe', point="50:50")
            print(f"Assign response: {response.status_code}")
            time.sleep(1)
            
            # Release focus point
            response = camera.send_command('exec_takemotion', com='releaseafframe')
            print(f"Release response: {response.status_code}")
            time.sleep(1)
        except Exception as e:
            print(f"Error with assign/release test: {e}")
            
        # Final test: Explore other options in takeready
        print("\n--- Testing other focus methods ---")
        try:
            # Try takeready
            response = camera.send_command('exec_takemotion', com='takeready', point="50:50")
            print(f"takeready response: {response.status_code}")
            time.sleep(1)
            
            # Try starttake
            try:
                response = camera.send_command('exec_takemotion', com='starttake', point="50:50")
                print(f"starttake response: {response.status_code}")
                time.sleep(1)
            except Exception as e:
                print(f"Error with starttake: {e}")
        except Exception as e:
            print(f"Error with takeready: {e}")
        
        # Clean up
        print("\nStopping live view...")
        camera.stop_liveview()
        
        print("Test complete")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
