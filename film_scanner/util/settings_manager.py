"""
Settings manager for the Film Scanner application.
Handles loading, saving, and accessing application settings.
"""
import os
import json
from typing import Any, Dict, Optional


class SettingsManager:
    """
    Manages application settings persistence and access.
    
    Provides a unified interface for storing and retrieving
    application settings across sessions.
    """
    
    DEFAULT_SETTINGS = {
        "output_directory": "~/Pictures/FilmScans",
        "live_view_quality": "0640x0480",
        "quality_index": 1,
        "show_fps": True,
        "auto_invert_negatives": False,
        "create_dated_subdirectories": True,
        "prefer_raw_files": True,
        "auto_start_live_view": True,
        "ui": {
            "show_camera_status": True,
            "camera_status_height": 30,
            "status_bar_color": "#222222",
            "status_text_color": "#ffffff"
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the settings manager.
        
        Args:
            config_file: Path to settings file
        """
        # Determine config file path
        if config_file is None:
            config_dir = os.path.expanduser("~/.config/film_scanner")
            # Create config directory if it doesn't exist
            if not os.path.exists(config_dir):
                try:
                    os.makedirs(config_dir)
                except Exception as e:
                    print(f"Warning: Could not create config directory: {e}")
            
            self.config_file = os.path.join(config_dir, "settings.json")
        else:
            self.config_file = config_file
        
        # Initialize settings with defaults
        self.settings = self.DEFAULT_SETTINGS.copy()
        
        # Load settings from file
        self.load_settings()
    
    def load_settings(self) -> bool:
        """
        Load settings from file.
        
        Returns:
            bool: True if settings were loaded successfully
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded_settings = json.load(f)
                
                # Update settings with loaded values
                self.settings.update(loaded_settings)
                return True
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        return False
    
    def save_settings(self) -> bool:
        """
        Save settings to file.
        
        Returns:
            bool: True if settings were saved successfully
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key (can use dot notation for nested settings)
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        # Handle nested keys with dot notation
        if '.' in key:
            parts = key.split('.')
            value = self.settings
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        
        # Handle simple keys
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key: Setting key (can use dot notation for nested settings)
            value: Setting value
        """
        # Handle nested keys with dot notation
        if '.' in key:
            parts = key.split('.')
            target = self.settings
            
            # Navigate to the correct nested dictionary
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            
            # Set the value
            target[parts[-1]] = value
        else:
            # Handle simple keys
            self.settings[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings.
        
        Returns:
            dict: All settings
        """
        return self.settings.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        self.settings = self.DEFAULT_SETTINGS.copy()
    
    def get_output_directory(self) -> str:
        """
        Get the configured output directory with expanded path.
        
        Returns:
            str: Output directory path
        """
        output_dir = self.get("output_directory", "~/Pictures/FilmScans")
        return os.path.expanduser(output_dir)
    
    def set_output_directory(self, directory: str) -> None:
        """
        Set the output directory.
        
        Args:
            directory: Output directory path
        """
        self.set("output_directory", directory)
