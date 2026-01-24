"""
Central state manager for the attendance tracking application.
Manages application state and notifies observers of state changes.
"""
from enum import Enum
from typing import Optional, Dict, Any, Callable
from PySide6.QtCore import QObject, Signal


class AppState(Enum):
    """Application states."""
    LOGGED_OUT = "logged_out"
    CHECKED_IN = "checked_in"
    ON_BREAK = "on_break"
    FORCE_BREAK = "force_break"


class StateManager(QObject):
    """Manages application state and provides signals for state changes."""
    
    # Signals
    state_changed = Signal(AppState)
    user_data_changed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self._state = AppState.LOGGED_OUT
        self._session_token: Optional[str] = None
        self._staff_settings: Optional[Dict[str, Any]] = None
        self._company_rules: Optional[Dict[str, Any]] = None
        self._user_name: Optional[str] = None
        self._check_in_time: Optional[str] = None
        self._break_start_time: Optional[str] = None
        self._late_by_minutes: Optional[int] = None
    
    @property
    def state(self) -> AppState:
        """Get current state."""
        return self._state
    
    @state.setter
    def state(self, new_state: AppState):
        """Set state and emit signal."""
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(new_state)
    
    @property
    def session_token(self) -> Optional[str]:
        """Get session token."""
        return self._session_token
    
    @property
    def staff_settings(self) -> Optional[Dict[str, Any]]:
        """Get staff settings."""
        return self._staff_settings
    
    @property
    def company_rules(self) -> Optional[Dict[str, Any]]:
        """Get company rules."""
        return self._company_rules
    
    @property
    def user_name(self) -> Optional[str]:
        """Get user name."""
        return self._user_name
    
    @property
    def check_in_time(self) -> Optional[str]:
        """Get check-in time."""
        return self._check_in_time
    
    @property
    def break_start_time(self) -> Optional[str]:
        """Get break start time."""
        return self._break_start_time
    
    @property
    def late_by_minutes(self) -> Optional[int]:
        """Get late by minutes."""
        return self._late_by_minutes
    
    @property
    def allow_screenshot(self) -> bool:
        """Check if screenshots are allowed."""
        if self._staff_settings:
            allow = self._staff_settings.get("allow_screenshot", False)
            # Handle both boolean and string "yes"/"no" formats
            if isinstance(allow, bool):
                return allow
            return allow == "yes" or allow == True
        return False
    
    @property
    def force_break_time(self) -> int:
        """Get force break time in seconds."""
        # force_break_time is in staff_settings, not company_rules
        if self._staff_settings:
            force_break_minutes = self._staff_settings.get("force_break_time", 5)  # Default 5 minutes
            return int(force_break_minutes) * 60  # Convert minutes to seconds
        return 300  # Default 5 minutes in seconds
    
    def set_login_data(self, session_token: str, staff_settings: Dict[str, Any], 
                      company_rules: Dict[str, Any], user_name: str):
        """Set login data after successful login."""
        self._session_token = session_token
        self._staff_settings = dict(staff_settings) if staff_settings else {}
        self._company_rules = company_rules
        self._user_name = user_name
        self.state = AppState.LOGGED_OUT  # Start logged out, need to check-in
        self.user_data_changed.emit({
            "user_name": user_name,
            "staff_settings": staff_settings,
            "company_rules": company_rules
        })

    def merge_staff_settings(self, updates: Dict[str, Any]) -> None:
        """Merge keys (e.g. from staff in dashboard stats) into _staff_settings."""
        if not updates:
            return
        if self._staff_settings is None:
            self._staff_settings = {}
        for k in ("force_break_time", "allow_screenshot", "shift_start", "shift_end", "timezone", "grace_period", "department"):
            if k in updates:
                self._staff_settings[k] = updates[k]
    
    def set_check_in(self, check_in_time: str, late_by_minutes: Optional[int] = None):
        """Set check-in data."""
        self._check_in_time = check_in_time
        self._late_by_minutes = late_by_minutes
        self.state = AppState.CHECKED_IN
    
    def set_break_start(self, break_start_time: str, is_force: bool = False):
        """Set break start data."""
        self._break_start_time = break_start_time
        self.state = AppState.FORCE_BREAK if is_force else AppState.ON_BREAK
    
    def set_break_end(self):
        """End break and return to checked in."""
        self._break_start_time = None
        self.state = AppState.CHECKED_IN
    
    def set_check_out(self):
        """Set check-out data."""
        self._check_in_time = None
        self._break_start_time = None
        self._late_by_minutes = None
        self.state = AppState.LOGGED_OUT
    
    def logout(self):
        """Clear all data and return to logged out state."""
        self._session_token = None
        self._staff_settings = None
        self._company_rules = None
        self._user_name = None
        self._check_in_time = None
        self._break_start_time = None
        self._late_by_minutes = None
        self.state = AppState.LOGGED_OUT
