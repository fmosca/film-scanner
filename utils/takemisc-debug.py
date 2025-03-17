#!/usr/bin/env python3
"""
Debug script specifically for the exec_takemisc command.
"""
import time
import sys
from olympuswifi.camera import OlympusCamera

def main():
    try:
        print("Connecting to camera...")
        camera = OlympusCamera()
        print(f"Connected to {camera.get_camera_model()}")
        
        # Print camera info
        print("\n--- Camera Info ---")
        print(f"Model: {camera.get_camera_model()}")
        print(f"Supported: {camera.get_supported()}")
        print(f"Versions: {camera.get_versions()}")
        
        # Check exact takemisc command structure
        print("\n--- exec_takemisc Command Details ---")
        takemisc_cmd = camera.commands.get('exec_takemisc')
        if takemisc_cmd:
            print(f"Method: {takemisc_cmd.method}")
            print(f"Arguments structure: {takemisc_cmd.args}")
        else:
            print("exec_takemisc command not found!")
        
        # Try to parse out the exact required arguments for ctrlzoom
        if takemisc_cmd and takemisc_cmd.args and 'com' in takemisc_cmd.args:
            if 'ctrlzoom' in takemisc_cmd.args['com']:
                print(f"\nctrlzoom options: {takemisc_cmd.args['com']['ctrlzoom']}")
                
                # Check move parameter options
                if 'move' in takemisc_cmd.args['com']['ctrlzoom']:
                    print(f"move options: {takemisc_cmd.args['com']['ctrlzoom']['move']}")
        
        # Switch to recording mode
        print("\n--- Switching to recording mode ---")
        camera.send_command('switch_cammode', mode='rec')
        time.sleep(1)
        
        # Start live view
        print("\n--- Starting live view ---")
        camera.start_liveview(port=40000, lvqty="0640x0480")
        time.sleep(1)
        
        # Test each available command in exec_takemisc
        print("\n--- Testing each exec_takemisc variant ---")
        if takemisc_cmd and takemisc_cmd.args and 'com' in takemisc_cmd.args:
            for com_name in takemisc_cmd.args['com'].keys():
                print(f"\nTesting com={com_name}")
                try:
                    if com_name == 'ctrlzoom':
                        # Test each move option
                        for move in takemisc_cmd.args['com']['ctrlzoom']['move'].keys():
                            if move == '*':  # Skip wildcard
                                continue
                            print(f"  Testing move={move}")
                            try:
                                # First try with point parameter
                                print(f"    With point='0160x0120'...")
                                response = camera.send_command('exec_takemisc', 
                                                             com='ctrlzoom', 
                                                             move=move,
                                                             point='0160x0120')
                                print(f"    Response: {response.status_code}")
                            except Exception as e:
                                print(f"    Error with point: {e}")
                                
                            try:
                                # Then try without point
                                print(f"    Without point...")
                                response = camera.send_command('exec_takemisc', 
                                                             com='ctrlzoom', 
                                                             move=move)
                                print(f"    Response: {response.status_code}")
                            except Exception as e:
                                print(f"    Error without point: {e}")
                    elif com_name == 'startliveview':
                        # Skip this as we're already in liveview
                        print("  Skipping (already in liveview)")
                    elif com_name == 'stopliveview':
                        # Skip this to avoid stopping liveview
                        print("  Skipping (would stop liveview)")
                    elif com_name == 'supermacromfinaflock':
                        # This needs multiple parameters
                        moves = ['nearstep', 'farstep', 'near', 'far', 'stop']
                        for move in moves:
                            print(f"  Testing move={move} movement=10")
                            try:
                                response = camera.send_command('exec_takemisc', 
                                                            com='supermacromfinaflock', 
                                                            move=move,
                                                            movement='10')
                                print(f"  Response: {response.status_code}")
                            except Exception as e:
                                print(f"  Error: {e}")
                    else:
                        # Try simple commands with no parameters
                        try:
                            response = camera.send_command('exec_takemisc', com=com_name)
                            print(f"  Response: {response.status_code}")
                        except Exception as e:
                            print(f"  Error: {e}")
                except Exception as e:
                    print(f"  General error: {e}")
        
        # Test alternative ways of magnifying
        print("\n--- Testing focus magnification alternatives ---")
        
        # Method 1: Double-tap focus point
        print("\nMethod 1: Double-tap focus point")
        try:
            point = "50:50"
            print(f"Setting focus point to {point}...")
            camera.send_command('exec_takemotion', com='assignafframe', point=point)
            time.sleep(0.5)
            print("Setting again to trigger magnification...")
            camera.send_command('exec_takemotion', com='assignafframe', point=point)
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
        
        # Method 2: Check for digital zoom
        print("\nMethod 2: Digital zoom controls")
        try:
            properties = camera.get_settable_propnames_and_values()
            for prop_name, values in properties.items():
                if 'digital' in prop_name.lower() or 'zoom' in prop_name.lower():
                    print(f"Found property: {prop_name} = {values}")
                    current = camera.get_camprop(prop_name)
                    print(f"Current value: {current}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Method 3: Try with manual focus assist
        print("\nMethod 3: Manual focus assist")
        try:
            properties = camera.get_settable_propnames_and_values()
            for prop_name, values in properties.items():
                if 'mf' in prop_name.lower() or 'assist' in prop_name.lower():
                    print(f"Found property: {prop_name} = {values}")
                    current = camera.get_camprop(prop_name)
                    print(f"Current value: {current}")
                    
                    # Try to toggle it
                    for val in values:
                        if val != current:
                            print(f"Setting {prop_name} to {val}...")
                            try:
                                camera.set_camprop(prop_name, val)
                                print("Success")
                                time.sleep(2)
                                
                                # Reset to original
                                camera.set_camprop(prop_name, current)
                                print("Reset to original")
                            except Exception as e:
                                print(f"Error setting property: {e}")
                            break
        except Exception as e:
            print(f"Error: {e}")
        
        # Clean up
        print("\nStopping live view...")
        camera.stop_liveview()
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
