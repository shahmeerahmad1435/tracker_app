"""
Activity listener for keyboard and mouse events.
Tracks last activity time for idle detection.
"""
from datetime import datetime
from typing import Optional
from threading import Lock
from pynput import keyboard, mouse
from PySide6.QtCore import QObject, Signal


class ActivityListener(QObject):
    """Listens for keyboard and mouse activity."""
    
    activity_detected = Signal()  # Emitted when any activity is detected
    
    def __init__(self):
        super().__init__()
        self._last_activity_time: datetime = datetime.now()
        self._lock = Lock()
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        self._is_listening = False
    
    def _on_activity(self):
        """Handle activity event."""
        with self._lock:
            self._last_activity_time = datetime.now()
        self.activity_detected.emit()
    
    def _on_key_press(self, key):
        """Handle key press."""
        self._on_activity()
    
    def _on_mouse_move(self, x, y):
        """Handle mouse move."""
        self._on_activity()
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Handle mouse click."""
        if pressed:
            self._on_activity()
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll."""
        self._on_activity()
    
    def start(self):
        """Start listening for activity."""
        if self._is_listening:
            return
        
        self._is_listening = True
        
        # Start keyboard listener
        self._keyboard_listener = keyboard.Listener(on_press=self._on_key_press)
        self._keyboard_listener.start()
        
        # Start mouse listener
        self._mouse_listener = mouse.Listener(
            on_move=self._on_mouse_move,
            on_click=self._on_mouse_click,
            on_scroll=self._on_mouse_scroll
        )
        self._mouse_listener.start()
    
    def stop(self):
        """Stop listening for activity."""
        if not self._is_listening:
            return
        
        self._is_listening = False
        
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
    
    def get_last_activity_time(self) -> datetime:
        """Get last activity time."""
        with self._lock:
            return self._last_activity_time
    
    def reset(self):
        """Reset last activity time to now."""
        with self._lock:
            self._last_activity_time = datetime.now()
