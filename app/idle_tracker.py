"""
Idle time tracker service.
Reports to API only when idle crosses company_rules thresholds: idle1_time, idle2_time, idle3_time (minutes).
"""
from datetime import datetime
from typing import List
from PySide6.QtCore import QObject, Signal, QTimer
from .activity_listener import ActivityListener
from .state_manager import StateManager, AppState
from .api_client import APIClient
from .config import IDLE_CHECK_INTERVAL_SECONDS


class IdleTracker(QObject):
    """Tracks idle time; reports to API only when crossing idle1 / idle2 / idle3 thresholds (in order)."""
    
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
        # Index of last threshold we reported (-1 = none, 0 = idle1, 1 = idle2, 2 = idle3)
        self._last_reported_threshold_index = -1
    
    def start(self):
        """Start idle tracking."""
        if self._is_active:
            return
        self._is_active = True
        self.activity_listener.reset()
        self._last_reported_threshold_index = -1
        self._timer.start(IDLE_CHECK_INTERVAL_SECONDS * 1000)
    
    def stop(self):
        """Stop idle tracking."""
        if not self._is_active:
            return
        self._is_active = False
        self._timer.stop()
    
    def _check_idle(self):
        """Check idle time; report to API only when crossing next threshold (idle1 → idle2 → idle3)."""
        if self.state_manager.state != AppState.CHECKED_IN:
            return
        
        last_activity = self.activity_listener.get_last_activity_time()
        now = datetime.now()
        idle_seconds = int((now - last_activity).total_seconds())
        thresholds: List[int] = self.state_manager.idle_report_thresholds_seconds  # [idle1_sec, idle2_sec, idle3_sec]
        
        self.idle_updated.emit(idle_seconds)
        
        if not thresholds:
            return
        
        # User became active again: below first threshold → reset so we report again when they go idle
        if idle_seconds < thresholds[0]:
            self._last_reported_threshold_index = -1
            return
        
        # Report when crossing the next threshold we haven't reported yet (in order)
        for i in range(len(thresholds)):
            if idle_seconds >= thresholds[i] and self._last_reported_threshold_index < i:
                try:
                    self.api_client.report_idle(idle_seconds)
                    self._last_reported_threshold_index = i
                except Exception as e:
                    print(f"Failed to report idle time: {e}")
                return
