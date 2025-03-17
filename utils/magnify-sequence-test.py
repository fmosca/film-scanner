#!/usr/bin/env python3
"""
Test script for trying specific command sequences for magnification.
"""
import time
import sys
from olympuswifi.camera import OlympusCamera

def main():
    try:
        print("Connecting to camera...")
        camera = OlympusCamera()
        print(f"Connected to {camera.get_camera_model()}")
        
        # Switch to recording mode
        print("Switching to recording mode...")
        camera.send_command('switch_cammode', mode='rec', lvqty="0640x0480")
        time.sleep(1)
        
        # Start live view
        print("Starting live view...")
        camera.start_liveview(port=40000, lvqty="0640x0480")
        time.sleep(1)
        
        # Test different sequences
        
        print("\n--- Sequence 1: Set focus point, then try zoom ---")
        try:
            # Set focus point
            print("Setting focus point...")
            camera.send_command('exec_takemotion', com='assignafframe', point="50:50")
            time.sleep(1)
            
            # Try zoom
            print("Trying zoom...")
            try:
                camera.send_command('exec_takemisc', com='ctrlzoom', move='telemove')
                print("Zoom command succeeded!")
            except Exception as e:
                print(f"Zoom failed: {e}")
        except Exception as e:
            print(f"Sequence 1 error: {e}")
        
        print("\n--- Sequence 2: takeready before zoom ---")
        try:
            # Set focus point with takeready
            print("Setting focus with takeready...")
            camera.send_command('exec_takemotion', com='takeready', point="50:50")
            time.sleep(1)
            
            # Try zoom
            print("Trying zoom...")
            try:
                camera.send_command('exec_takemisc', com='ctrlzoom', move='telemove')
                print("Zoom command succeeded!")
            except Exception as e:
                print(f"Zoom failed: {e}")
        except Exception as e:
            print(f"Sequence 2 error: {e}")
        
        print("\n--- Sequence 3: Setup zoom with movement parameters ---")
        try:
            # Try zoom with movement param
            for value in ['1', '2', '3', '10', '100']:
                print(f"Trying telemove with movement={value}...")
                try:
                    camera.send_command('exec_takemisc', com='ctrlzoom', move='telemove', movement=value)
                    print("Zoom command succeeded!")
                    break
                except Exception as e:
                    print(f"Failed with movement={value}: {e}")
        except Exception as e:
            print(f"Sequence 3 error: {e}")
            
        # Try to cancel zoom
        print("\nTurning off zoom...")
        try:
            camera.send_command('exec_takemisc', com='ctrlzoom', move='off')
            print("Zoom off succeeded")
        except Exception as e:
            print(f"Zoom off failed: {e}")
            
        print("\n--- Sequence 4: Exploring alternative parameters ---")
        try:
            # Try various parameter combinations
            # Parameter names to try
            params = ['value', 'step', 'zoom', 'level', 'mag', 'magnification']
            
            # Values to try
            values = ['1', '2', '3', '10']
            
            for param in params:
                for value in values:
                    print(f"Trying telemove with {param}={value}...")
                    try:
                        # Create params dict dynamically
                        extra_params = {'com': 'ctrlzoom', 'move': 'telemove', param: value}
                        camera.send_command('exec_takemisc', **extra_params)
                        print(f"Success with {param}={value}!")
                        
                        # Try to turn off zoom
                        camera.send_command('exec_takemisc', com='ctrlzoom', move='off')
                        break  # Found a working param, stop trying
                    except Exception as e:
                        if 'not supported' in str(e):
                            print(f"Parameter '{param}' not supported")
                        else:
                            print(f"Failed: {e}")
        except Exception as e:
            print(f"Sequence 4 error: {e}")
            
        print("\n--- Sequence 5: Liveview controls ---")
        try:
            # Stop and restart liveview with special options
            print("Stopping liveview...")
            camera.stop_liveview()
            time.sleep(1)
            
            # Try restart with magnify flag
            print("Restarting liveview with focus flag...")
            try:
                # Try different combinations of parameters
                flags = ['magnify', 'focus', 'mag', 'zoom']
                for flag in flags:
                    try:
                        print(f"Trying with {flag}=on...")
                        camera.send_command('exec_takemisc', com='startliveview', port=40000, **{flag: 'on'})
                        print(f"Success with {flag}=on")
                    except Exception as e:
                        print(f"Failed with {flag}: {e}")
                
                # Restart normally if all failed
                print("Restarting liveview normally...")
                camera.start_liveview(port=40000, lvqty="0640x0480")
            except Exception as e:
                print(f"Restart error: {e}")
                # Make sure liveview is started
                camera.start_liveview(port=40000, lvqty="0640x0480")
        except Exception as e:
            print(f"Sequence 5 error: {e}")
        
        # Wait a moment to observe effects
        time.sleep(2)
        
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
