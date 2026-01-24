"""
Idle time tracker service.
Tracks user idle time and reports to API when thresholds are crossed.
"""
from datetime import datetime, timedelta
from typing import Optional
from PySide6.QtCore import QObject, Signal, QTimer
from .activity_listener import ActivityListener
from .state_manager import StateManager, AppState
from .api_client import APIClient
from .config import IDLE_CHECK_INTERVAL_SECONDS


class IdleTracker(QObject):
    """Tracks idle time and reports to API."""
    
    idle_updated = Signal(int)  # Emitted with idle_seconds
    
    def __init__(self, state_manager: StateManager, api_client: APIClient, 
                 activity_listener: ActivityListener):
        super().__init__()
        self.state_manager = state_manager
        self.api_client = api_client
        self.activity_listener = activity_listener
        
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_idle)
        self._is_active = False
        self._last_reported_idle = 0
    
    def start(self):
        """Start idle tracking."""
        if self._is_active:
            return
        
        self._is_active = True
        self.activity_listener.reset()
        self._last_reported_idle = 0
        self._timer.start(IDLE_CHECK_INTERVAL_SECONDS * 1000)  # Convert to milliseconds
    
    def stop(self):
        """Stop idle tracking."""
        if not self._is_active:
            return
        
        self._is_active = False
        self._timer.stop()
    
    def _check_idle(self):
        """Check current idle time and report if needed."""
        # Only track when checked in
        if self.state_manager.state != AppState.CHECKED_IN:
            return
        
        # Calculate idle seconds
        last_activity = self.activity_listener.get_last_activity_time()
        now = datetime.now()
        idle_seconds = int((now - last_activity).total_seconds())
        
        # Emit signal for UI updates
        self.idle_updated.emit(idle_seconds)
        
        # Report to API if threshold crossed (report every 30 seconds of change)
        if abs(idle_seconds - self._last_reported_idle) >= 30:
            try:
                self.api_client.report_idle(idle_seconds)
                self._last_reported_idle = idle_seconds
            except Exception as e:
                print(f"Failed to report idle time: {e}")
