#!/usr/bin/env python3
"""
Camera Explorer script for discovering Olympus camera capabilities
Dumps all available commands, properties, and their values
"""
import sys
import os
import json
import argparse
from olympuswifi.camera import OlympusCamera


class CameraExplorer:
    """
    Explores Olympus camera capabilities and dumps them to files
    for later exploration and reverse engineering.
    """
    
    def __init__(self, output_dir="camera_output", verbose=False):
        """Initialize the camera explorer with path for output files"""
        self.output_dir = output_dir
        self.verbose = verbose
        self.camera = None
        self.log(f"Initializing Camera Explorer with output to: {output_dir}")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def log(self, message):
        """Log messages if verbose mode is on"""
        if self.verbose:
            print(message)
    
    def connect(self):
        """Connect to the camera and retrieve initial information"""
        try:
            self.log("Connecting to camera...")
            self.camera = OlympusCamera()
            self.log(f"Connected to {self.camera.get_camera_model()}")
            return True
        except Exception as e:
            print(f"Error connecting to camera: {e}")
            return False
    
    def save_json(self, data, filename):
        """Save data as JSON to the specified file"""
        path = os.path.join(self.output_dir, filename)
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)
            self.log(f"Saved data to {path}")
            return True
        except Exception as e:
            print(f"Error saving {path}: {e}")
            return False
    
    def save_text(self, text, filename):
        """Save text to the specified file"""
        path = os.path.join(self.output_dir, filename)
        try:
            with open(path, 'w') as f:
                f.write(text)
            self.log(f"Saved text to {path}")
            return True
        except Exception as e:
            print(f"Error saving {path}: {e}")
            return False
    
    def dump_camera_info(self):
        """Dump basic camera information"""
        info = {
            "model": self.camera.get_camera_model(),
            "info": self.camera.get_camera_info(),
            "versions": self.camera.get_versions(),
            "supported": list(self.camera.get_supported())
        }
        return self.save_json(info, "camera_info.json")
    
    def dump_commands(self):
        """Dump all available commands and their parameters"""
        commands = {}
        for cmd_name, cmd_descr in self.camera.get_commands().items():
            commands[cmd_name] = {
                "method": cmd_descr.method,
                "args": self._serialize_args(cmd_descr.args)
            }
        return self.save_json(commands, "commands.json")
    
    def _serialize_args(self, args):
        """Convert command args to serializable format"""
        if args is None:
            return None
            
        result = {}
        for key, value in args.items():
            if value is None:
                result[key] = None
            else:
                result[key] = self._serialize_args(value)
        return result
    
    def dump_properties(self):
        """Dump all camera properties and their possible values"""
        try:
            properties = self.camera.get_settable_propnames_and_values()
            # Convert properties dict to serializable format (lists instead of tuple/set)
            serializable = {k: list(v) for k, v in properties.items()}
            return self.save_json(serializable, "properties.json")
        except Exception as e:
            print(f"Error dumping properties: {e}")
            return False
    
    def execute_command(self, command, **params):
        """Execute a specific command and save the result"""
        self.log(f"Executing command: {command} with params: {params}")
        try:
            response = self.camera.send_command(command, **params)
            
            # Save response based on content type
            if 'Content-Type' in response.headers:
                content_type = response.headers['Content-Type']
                
                if content_type == 'text/xml':
                    # Save XML response as text
                    self.save_text(response.text, f"response_{command}.xml")
                elif content_type.startswith('text/'):
                    # Save other text responses
                    self.save_text(response.text, f"response_{command}.txt")
                elif content_type.startswith('image/'):
                    # Save binary image data
                    with open(os.path.join(self.output_dir, f"response_{command}.jpg"), 'wb') as f:
                        f.write(response.content)
                else:
                    # Save other binary data
                    with open(os.path.join(self.output_dir, f"response_{command}.bin"), 'wb') as f:
                        f.write(response.content)
            else:
                # If no content type, save as text
                self.save_text(response.text, f"response_{command}.txt")
                
            self.log(f"Saved response for command {command}")
            return True
        except Exception as e:
            print(f"Error executing command {command}: {e}")
            return False
    
    def explore_magnification(self):
        """Focus on exploring magnification capabilities"""
        # First try to switch to rec mode
        self.log("Exploring magnification capabilities...")
        
        try:
            # Switch to recording mode
            self.camera.send_command('switch_cammode', mode='rec')
            
            # Explore zoom-related properties
            zoom_props = []
            for prop in self.camera.get_settable_propnames_and_values().keys():
                if 'zoom' in prop.lower() or 'magnif' in prop.lower():
                    zoom_props.append(prop)
                    self.log(f"Found zoom-related property: {prop}")
            
            if zoom_props:
                self.save_json(zoom_props, "zoom_properties.json")
            
            # Look for zoom-related commands
            zoom_cmds = []
            for cmd_name, cmd_descr in self.camera.get_commands().items():
                if 'zoom' in cmd_name.lower():
                    zoom_cmds.append(cmd_name)
                    self.log(f"Found zoom-related command: {cmd_name}")
                    
                    # Try to execute the command with default values
                    try:
                        response = self.camera.send_command(cmd_name)
                        self.log(f"Executed {cmd_name}: {response.status_code}")
                    except Exception as e:
                        self.log(f"Could not execute {cmd_name}: {e}")
            
            if zoom_cmds:
                self.save_json(zoom_cmds, "zoom_commands.json")
                
            return True
        except Exception as e:
            print(f"Error exploring magnification: {e}")
            return False
    
    def explore_liveview_options(self):
        """Explore available live view options"""
        try:
            # Check for live view settings
            liveview_settings = {}
            
            # Look in switch_cammode rec options for liveview quality
            commands = self.camera.get_commands()
            if 'switch_cammode' in commands and commands['switch_cammode'].args:
                args = commands['switch_cammode'].args
                if 'mode' in args and 'rec' in args['mode']:
                    rec_options = args['mode']['rec']
                    if rec_options and 'lvqty' in rec_options:
                        liveview_settings['qualities'] = list(rec_options['lvqty'].keys())
            
            # Look for live view commands
            liveview_cmds = []
            for cmd_name in commands:
                if 'live' in cmd_name.lower() or 'lv' in cmd_name.lower():
                    liveview_cmds.append(cmd_name)
            
            liveview_settings['commands'] = liveview_cmds
            
            if liveview_settings:
                self.save_json(liveview_settings, "liveview_options.json")
            
            return True
        except Exception as e:
            print(f"Error exploring live view options: {e}")
            return False
    
    def explore_focus_options(self):
        """Explore available focus control options"""
        try:
            # Look for focus-related properties
            focus_props = []
            for prop in self.camera.get_settable_propnames_and_values().keys():
                if 'focus' in prop.lower() or 'af' in prop.lower():
                    focus_props.append(prop)
                    
            # Look for focus-related commands
            focus_cmds = []
            for cmd_name in self.camera.get_commands():
                if 'focus' in cmd_name.lower() or 'af' in cmd_name.lower():
                    focus_cmds.append(cmd_name)
            
            focus_options = {
                'properties': focus_props,
                'commands': focus_cmds
            }
            
            if focus_options['properties'] or focus_options['commands']:
                self.save_json(focus_options, "focus_options.json")
            
            return True
        except Exception as e:
            print(f"Error exploring focus options: {e}")
            return False
    
    def switch_to_rec_mode(self):
        """Switch the camera to recording mode"""
        try:
            self.log("Switching to recording mode...")
            self.camera.send_command('switch_cammode', mode='rec')
            self.log("Successfully switched to recording mode")
            return True
        except Exception as e:
            print(f"Error switching to recording mode: {e}")
            return False
    
    def dump_properties_in_rec_mode(self):
        """Dump camera properties specifically in recording mode"""
        if not self.switch_to_rec_mode():
            return False
            
        # Make a new directory for rec mode properties
        rec_dir = os.path.join(self.output_dir, "rec_mode")
        if not os.path.exists(rec_dir):
            os.makedirs(rec_dir)
            
        old_output_dir = self.output_dir
        self.output_dir = rec_dir
        
        # Get all camera properties in rec mode
        result = self.dump_properties()
        
        # Get detailed property descriptions
        try:
            self.log("Getting detailed property descriptions in rec mode...")
            response = self.camera.send_command("get_camprop", com="desc", propname="desclist")
            if response:
                self.save_text(response.text, "property_descriptions.xml")
                
                # Also get individual property values
                properties = self.camera.get_settable_propnames_and_values()
                for prop_name in properties.keys():
                    try:
                        prop_response = self.camera.send_command("get_camprop", com="get", propname=prop_name)
                        if prop_response:
                            self.save_text(prop_response.text, f"property_{prop_name}_value.xml")
                    except Exception as e:
                        self.log(f"Error getting property {prop_name}: {e}")
        except Exception as e:
            print(f"Error getting property descriptions: {e}")
            
        # Restore original output directory
        self.output_dir = old_output_dir
        return result
        
    def run_exploration(self):
        """Run the complete exploration process"""
        if not self.connect():
            return False
        
        # Dump basic camera information
        self.dump_camera_info()
        
        # Dump all commands and properties
        self.dump_commands()
        
        # Switch to recording mode and explore
        self.log("Exploring camera in recording mode...")
        self.dump_properties_in_rec_mode()
        
        # Specific explorations in recording mode
        if self.switch_to_rec_mode():
            self.explore_magnification()
            self.explore_liveview_options()
            self.explore_focus_options()
            
            # Try execute recording-mode specific commands
            rec_commands_to_try = [
                "exec_takemisc",  # This handles live view
                "get_camprop"     # This gets camera properties
            ]
            
            for cmd in rec_commands_to_try:
                if cmd == "exec_takemisc":
                    # Try to get liverview commands
                    self.execute_command(cmd, com="getlastjpg")
                    self.execute_command(cmd, com="ctrlzoom", move="off")
                elif cmd == "get_camprop":
                    # Get various properties
                    self.execute_command(cmd, com="desc", propname="desclist")
                    # Try to find zoom/magnification related properties
                    for prop in ["magnifingLiveViewScale", "magnifyingLiveViewScale"]:
                        self.execute_command(cmd, com="get", propname=prop)
        
        # Additional focus on magnification modes and navigation
        if self.switch_to_rec_mode():
            self.log("Exploring magnification control in more detail...")
            # Try to detect magnification controls
            try:
                # Sometimes magnification is controlled by these commands
                self.execute_command("exec_takemisc", com="ctrlzoom", move="widemove")
                self.execute_command("exec_takemisc", com="ctrlzoom", move="telemove")
                
                # Try to find MF assist functionality (which often includes magnification)
                for prop in self.camera.get_settable_propnames_and_values().keys():
                    if "assist" in prop.lower() or "magnif" in prop.lower():
                        possible_values = self.camera.get_settable_propnames_and_values()[prop]
                        self.log(f"Found potential magnification property: {prop} with values: {possible_values}")
                        
                        # Try setting each value
                        original_value = self.camera.get_camprop(prop)
                        magnify_results = {"property": prop, "original_value": original_value, "results": {}}
                        
                        for value in possible_values:
                            try:
                                self.log(f"Setting {prop} to {value}...")
                                self.camera.set_camprop(prop, value)
                                magnify_results["results"][value] = "success"
                            except Exception as e:
                                self.log(f"Error setting {prop} to {value}: {e}")
                                magnify_results["results"][value] = f"error: {str(e)}"
                                
                        # Restore original value
                        try:
                            self.camera.set_camprop(prop, original_value)
                        except:
                            pass
                            
                        self.save_json(magnify_results, "magnification_tests.json")
            except Exception as e:
                self.log(f"Error during detailed magnification exploration: {e}")
        
        self.log("Exploration complete!")
        return True


def main():
    parser = argparse.ArgumentParser(description="Explore Olympus camera capabilities")
    parser.add_argument("--output", "-o", default="camera_output", 
                        help="Output directory for exploration results")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Enable verbose output")
    parser.add_argument("--command", "-c", 
                        help="Execute a specific camera command")
    parser.add_argument("--params", "-p", 
                        help="Parameters for the command in key=value format, comma-separated")
    parser.add_argument("--rec-mode", "-r", action="store_true",
                        help="Switch to recording mode before executing command")
    parser.add_argument("--only-rec", action="store_true",
                        help="Only explore camera in recording mode")
    
    args = parser.parse_args()
    
    explorer = CameraExplorer(args.output, args.verbose)
    
    if args.command:
        if not explorer.connect():
            return 1
            
        # Switch to rec mode if requested
        if args.rec_mode:
            if not explorer.switch_to_rec_mode():
                print("Failed to switch to recording mode")
                return 1
            
        # Parse command parameters
        params = {}
        if args.params:
            param_list = args.params.split(",")
            for param in param_list:
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[key.strip()] = value.strip()
        
        # Execute the specific command
        explorer.execute_command(args.command, **params)
    else:
        if args.only_rec:
            # Only explore in recording mode
            if not explorer.connect():
                return 1
                
            explorer.dump_camera_info()
            explorer.dump_commands()
            explorer.dump_properties_in_rec_mode()
            explorer.explore_magnification()
            explorer.explore_liveview_options()
            explorer.explore_focus_options()
        else:
            # Run full exploration
            explorer.run_exploration()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())