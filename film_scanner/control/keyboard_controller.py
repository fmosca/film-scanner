"""
Keyboard controller for the Film Scanner application.
Handles keyboard events and routes them to appropriate actions.
"""
import tkinter as tk
from typing import Dict, Callable, Any, Optional

from .state_manager import StateManager, AppState


class KeyboardController:
    """
    Handles keyboard input and routes to appropriate actions.
    
    Uses the Command pattern to manage key bindings and supports
    state-dependent keyboard shortcuts.
    """
    
    def __init__(self, root: tk.Tk, state_manager: StateManager):
        """
        Initialize the keyboard controller.
        
        Args:
            root: Root tkinter window for binding keys
            state_manager: Application state manager
        """
        self.root = root
        self.state_manager = state_manager
        
        # Command registry maps (key, state) to handler functions
        self._commands: Dict[tuple, Callable] = {}
        
        # Global commands (work in any state)
        self._global_commands: Dict[str, Callable] = {}
        
        # Debug flag for showing command info
        self.debug = False
    
    def register_command(self, key: str, handler: Callable, states: Optional[list] = None):
        """
        Register a command for a specific key in specific states.
        
        Args:
            key: Key identifier (e.g., "s", "<Escape>")
            handler: Function to call when key is pressed
            states: List of states where this key is active (None for all states)
        """
        if states is None:
            # Global command for all states
            self._global_commands[key] = handler
        else:
            # State-specific commands
            for state in states:
                self._commands[(key, state)] = handler
        
        # Ensure key is bound
        self._bind_key(key)
    
    def _bind_key(self, key: str):
        """
        Bind a key to the handler function.
        
        Args:
            key: Key identifier
        """
        # Normalize key name for Tkinter binding
        if len(key) == 1:
            # Single character keys
            bind_key = key.lower()
            self.root.bind(bind_key, lambda e: self._handle_key_press(bind_key))
            
            # Also bind uppercase version for when Shift is pressed
            if key.isalpha():
                bind_key_upper = key.upper()
                self.root.bind(bind_key_upper, lambda e: self._handle_key_press(bind_key))
        else:
            # Special keys like "<Escape>"
            self.root.bind(key, lambda e: self._handle_key_press(key))
    
    def _handle_key_press(self, key: str):
        """
        Handle a key press event.
        
        Args:
            key: Pressed key
        """
        current_state = self.state_manager.current_state
        
        # Print debug info if enabled
        if self.debug:
            print(f"Key pressed: {key} in state {current_state}")
        
        # Check for state-specific command
        command_key = (key, current_state)
        if command_key in self._commands:
            self._commands[command_key]()
            return
        
        # Check for global command
        if key in self._global_commands:
            self._global_commands[key]()
            return
        
        # No command found
        if self.debug:
            print(f"No command registered for key {key} in state {current_state}")
    
    def register_default_commands(self, command_map: Dict[str, Callable]):
        """
        Register a set of default commands.
        
        Args:
            command_map: Dictionary mapping keys to handler functions
                         Format: {"key": handler_function}
        """
        for key, handler in command_map.items():
            self.register_command(key, handler)
    
    def register_state_commands(self, state: AppState, command_map: Dict[str, Callable]):
        """
        Register commands for a specific state.
        
        Args:
            state: Application state
            command_map: Dictionary mapping keys to handler functions
                         Format: {"key": handler_function}
        """
        for key, handler in command_map.items():
            self.register_command(key, handler, states=[state])
    
    def enable_debug(self, enabled: bool = True):
        """
        Enable or disable debug output.
        
        Args:
            enabled: Whether debug output should be enabled
        """
        self.debug = enabled
