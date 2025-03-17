#!/usr/bin/env python3
"""
Test script exploring focus assist functionality which might enable magnification.
"""
import time
import sys
from olympuswifi.camera import OlympusCamera

def main():
    try:
        print("Connecting to camera...")
        camera = OlympusCamera()
        print(f"Connected to {camera.get_camera_model()}")
        
        # Explore available camera properties
        print("\n--- Exploring camera properties ---")
        properties = camera.get_settable_propnames_and_values()
        
        # Get takemode options
        if 'takemode' in properties:
            print(f"Available takemodes: {properties['takemode']}")
            
            # Get current takemode
            try:
                current_mode = camera.get_camprop('takemode')
                print(f"Current takemode: {current_mode}")
            except:
                print("Could not get current takemode")
        
        # Switch to manual mode (might be needed for focus assist)
        print("\n--- Switching to Manual mode ---")
        try:
            if 'takemode' in properties and 'M' in properties['takemode']:
                camera.set_camprop('takemode', 'M')
                print("Switched to manual mode")
            else:
                print("Manual mode not available or takemode not settable")
        except Exception as e:
            print(f"Failed to set manual mode: {e}")
        
        # Switch to recording mode
        print("Switching to recording mode...")
        camera.send_command('switch_cammode', mode='rec', lvqty="0640x0480")
        time.sleep(1)
        
        # Start live view
        print("Starting live view...")
        camera.start_liveview(port=40000, lvqty="0640x0480")
        time.sleep(1)
        
        # Check for focus assist / magnify properties
        print("\n--- Checking for focus assist properties ---")
        focus_props = []
        
        for prop_name in properties:
            if ('focus' in prop_name.lower() or 'magnif' in prop_name.lower() or 
                'assist' in prop_name.lower() or 'mf' in prop_name.lower() or
                'zoom' in prop_name.lower()):
                focus_props.append(prop_name)
                print(f"Found focus property: {prop_name} = {properties[prop_name]}")
                
                # Get current value
                try:
                    current = camera.get_camprop(prop_name)
                    print(f"Current value: {current}")
                except:
                    print(f"Could not get current value for {prop_name}")
        
        # Try to toggle focus assist properties
        if focus_props:
            print("\n--- Testing focus assist properties ---")
            for prop in focus_props:
                values = properties[prop]
                
                # Skip if no values available
                if not values:
                    continue
                    
                # Get current value
                try:
                    current = camera.get_camprop(prop)
                    print(f"\nProperty: {prop}, Current: {current}")
                    
                    # Try each value
                    for value in values:
                        if value != current:
                            print(f"Setting {prop} to {value}...")
                            try:
                                camera.set_camprop(prop, value)
                                print("Success!")
                                time.sleep(3)  # Let it take effect
                                
                                # Reset to original value
                                print(f"Resetting {prop} to {current}...")
                                camera.set_camprop(prop, current)
                            except Exception as e:
                                print(f"Failed to set {prop} to {value}: {e}")
                except Exception as e:
                    print(f"Error testing {prop}: {e}")
        else:
            print("No focus assist properties found")
            
        # Try manual focus with specific commands
        print("\n--- Testing manual focus commands ---")
        
        # 1. First try to set manual focus mode if possible
        mf_mode_set = False
        for prop in focus_props:
            if prop.lower().endswith('mode') and 'mf' in str(properties[prop]).lower():
                for value in properties[prop]:
                    if 'mf' in value.lower() or 'manual' in value.lower():
                        try:
                            print(f"Setting {prop} to {value}...")
                            camera.set_camprop(prop, value)
                            print("Manual focus mode set")
                            mf_mode_set = True
                            break
                        except Exception as e:
                            print(f"Failed to set MF mode: {e}")
            if mf_mode_set:
                break
                
        # 2. Try using supermacromfinaflock
        print("\nTesting supermacromfinaflock...")
        moves = ['near', 'far', 'nearstep', 'farstep', 'stop']
        for move in moves:
            try:
                # Try different movement values
                for movement in ["1", "5", "10", "20"]:
                    print(f"Testing move={move}, movement={movement}...")
                    response = camera.send_command('exec_takemisc', com='supermacromfinaflock', move=move, movement=movement)
                    print(f"Response: {response.status_code}")
                    time.sleep(1)
            except Exception as e:
                print(f"Error with {move}: {e}")
                
        # 3. Test focus-related commands
        print("\nTesting focus commands...")
        try:
            # First set focus point
            camera.send_command('exec_takemotion', com='assignafframe', point="50:50")
            print("Focus point set")
            time.sleep(1)
            
            # Try specific focus commands
            focus_commands = [
                ('assignafframe', {'point': '50:50'}),
                ('takeready', {'point': '50:50'}),
                ('releaseafframe', {})
            ]
            
            for cmd, params in focus_commands:
                print(f"Testing {cmd}...")
                try:
                    response = camera.send_command('exec_takemotion', com=cmd, **params)
                    print(f"Response: {response.status_code}")
                    time.sleep(1)
                except Exception as e:
                    print(f"Error with {cmd}: {e}")
        except Exception as e:
            print(f"Error testing focus commands: {e}")
                
        # Clean up
        print("\nStopping live view...")
        camera.stop_liveview()
        
        # Reset takemode if needed
        if 'takemode' in properties:
            try:
                original_mode = properties['takemode'][0]  # Default to first option
                camera.set_camprop('takemode', original_mode)
                print(f"Reset takemode to {original_mode}")
            except:
                print("Could not reset takemode")
        
        print("Test complete")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
