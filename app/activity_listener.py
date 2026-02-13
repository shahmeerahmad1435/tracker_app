"""
Activity listener for keyboard and mouse events.
Tracks last activity time for idle detection.
Provides system-level idle time when available (macOS/Windows) for ending force break.
"""
import sys
from datetime import datetime
from typing import Optional
from threading import Lock
from pynput import keyboard, mouse
from PySide6.QtCore import QObject, Signal


def _seconds_since_last_system_input() -> Optional[float]:
    """Seconds since last system-wide mouse/keyboard input. None if not available."""
    try:
        if sys.platform == "darwin":
            # macOS: CoreGraphics HID (mouse/keyboard) idle time
            try:
                from ctypes import cdll, c_uint32
                CG = cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
                # kCGEventSourceStateHIDSystemState = 1, kCGAnyInputEventType = ~0 (any input)
                CG.CGEventSourceSecondsSinceLastEventType.argtypes = [c_uint32, c_uint32]
                CG.CGEventSourceSecondsSinceLastEventType.restype = float
                return CG.CGEventSourceSecondsSinceLastEventType(1, 0xFFFFFFFF)
            except Exception:
                return None
        if sys.platform == "win32":
            # Windows: GetLastInputInfo
            try:
                from ctypes import windll, Structure, c_uint, byref
                class LASTINPUTINFO(Structure):
                    _fields_ = [("cbSize", c_uint), ("dwTime", c_uint)]
                lii = LASTINPUTINFO()
                lii.cbSize = 8
                if windll.user32.GetLastInputInfo(byref(lii)):
                    millis = windll.kernel32.GetTickCount() - lii.dwTime
                    return millis / 1000.0
            except Exception:
                return None
    except Exception:
        pass
    return None


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

    def get_seconds_since_last_activity(self) -> float:
        """Seconds since last activity. Uses system idle time (macOS/Windows) when available, else our listener."""
        now = datetime.now()
        with self._lock:
            app_seconds = (now - self._last_activity_time).total_seconds()
        system_seconds = _seconds_since_last_system_input()
        if system_seconds is not None:
            return min(app_seconds, system_seconds)
        return app_seconds
    
    def reset(self):
        """Reset last activity time to now."""
        with self._lock:
            self._last_activity_time = datetime.now()
