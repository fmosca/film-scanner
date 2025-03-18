"""
State manager for the Film Scanner application.
Manages application state and transitions between states.
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable, Dict, List


class AppState(Enum):
    """Enum representing the different states of the application."""
    STARTUP = auto()
    LIVE_VIEW = auto()
    TAKING_PHOTO = auto()
    LOADING_PREVIEW = auto()
    PREVIEW = auto()
    DOWNLOADING = auto()
    SHUTDOWN = auto()
    ERROR = auto()


@dataclass
class StateChangeEvent:
    """Event data for state changes."""
    previous_state: AppState
    new_state: AppState
    context: Optional[dict] = None


class StateManager:
    """
    Manages application state transitions and notifications.
    
    This class enforces valid state transitions and notifies 
    subscribers when the state changes.
    """
    
    def __init__(self, initial_state: AppState = AppState.STARTUP):
        """
        Initialize the state manager.
        
        Args:
            initial_state: Initial application state
        """
        self._current_state = initial_state
        self._previous_state = None
        self._context = {}  # Shared context between states
        self._subscribers = []
        
        # Define valid state transitions
        self._valid_transitions = {
            AppState.STARTUP: [AppState.LIVE_VIEW, AppState.ERROR, AppState.SHUTDOWN],
            AppState.LIVE_VIEW: [AppState.TAKING_PHOTO, AppState.ERROR, AppState.SHUTDOWN],
            AppState.TAKING_PHOTO: [AppState.LOADING_PREVIEW, AppState.LIVE_VIEW, AppState.ERROR],
            AppState.LOADING_PREVIEW: [AppState.PREVIEW, AppState.LIVE_VIEW, AppState.ERROR],
            AppState.PREVIEW: [AppState.DOWNLOADING, AppState.LIVE_VIEW, AppState.ERROR],
            AppState.DOWNLOADING: [AppState.LIVE_VIEW, AppState.ERROR],
            AppState.ERROR: [AppState.LIVE_VIEW, AppState.SHUTDOWN],
            AppState.SHUTDOWN: []  # Terminal state
        }
        
        # Transition handlers (functions to call during specific transitions)
        self._transition_handlers: Dict[tuple, List[Callable]] = {}
    
    @property
    def current_state(self) -> AppState:
        """Get the current application state."""
        return self._current_state
    
    @property
    def previous_state(self) -> Optional[AppState]:
        """Get the previous application state."""
        return self._previous_state
    
    @property
    def context(self) -> dict:
        """Get the current state context."""
        return self._context.copy()  # Return a copy to prevent direct modification
    
    def can_transition_to(self, new_state: AppState) -> bool:
        """
        Check if transitioning to the given state is valid.
        
        Args:
            new_state: Target state
            
        Returns:
            bool: True if the transition is valid
        """
        return new_state in self._valid_transitions.get(self._current_state, [])
    
    def transition_to(self, new_state: AppState, context_updates: Optional[dict] = None) -> bool:
        """
        Transition to a new state if valid.
        
        Args:
            new_state: Target state
            context_updates: Updates to the state context
            
        Returns:
            bool: True if the transition was successful
        """
        if not self.can_transition_to(new_state):
            return False
        
        # Update context if provided
        if context_updates:
            self._context.update(context_updates)
        
        # Record the state change
        self._previous_state = self._current_state
        self._current_state = new_state
        
        # Create event data
        event = StateChangeEvent(
            previous_state=self._previous_state,
            new_state=self._current_state,
            context=self.context
        )
        
        # Call transition handlers
        transition_key = (self._previous_state, self._current_state)
        if transition_key in self._transition_handlers:
            for handler in self._transition_handlers[transition_key]:
                handler(event)
        
        # Notify subscribers
        self._notify_subscribers(event)
        
        return True
    
    def add_transition_handler(self, from_state: AppState, to_state: AppState, 
                              handler: Callable[[StateChangeEvent], None]) -> None:
        """
        Add a handler for a specific state transition.
        
        Args:
            from_state: Source state
            to_state: Target state
            handler: Function to call when this transition occurs
        """
        transition_key = (from_state, to_state)
        if transition_key not in self._transition_handlers:
            self._transition_handlers[transition_key] = []
        self._transition_handlers[transition_key].append(handler)
    
    def subscribe(self, callback: Callable[[StateChangeEvent], None]) -> None:
        """
        Subscribe to state change events.
        
        Args:
            callback: Function to call when state changes
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[StateChangeEvent], None]) -> None:
        """
        Unsubscribe from state change events.
        
        Args:
            callback: Previously registered callback function
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def _notify_subscribers(self, event: StateChangeEvent) -> None:
        """
        Notify all subscribers of a state change.
        
        Args:
            event: State change event data
        """
        for subscriber in self._subscribers:
            subscriber(event)
    
    def set_context_value(self, key: str, value) -> None:
        """
        Set a value in the state context.
        
        Args:
            key: Context key
            value: Value to store
        """
        self._context[key] = value
    
    def get_context_value(self, key: str, default=None):
        """
        Get a value from the state context.
        
        Args:
            key: Context key
            default: Default value if key not found
            
        Returns:
            Value from context or default
        """
        return self._context.get(key, default)
