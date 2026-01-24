"""
Screenshot capture service.
Captures full-screen screenshots and uploads to API.
"""
import base64
from PySide6.QtCore import QObject, Signal, QTimer
from mss import mss
from mss.tools import to_png
from .state_manager import StateManager, AppState
from .api_client import APIClient
from .config import SCREENSHOT_INTERVAL_SECONDS


class ScreenshotService(QObject):
    """Captures and uploads screenshots."""
    
    screenshot_captured = Signal()  # Emitted after successful capture
    
    def __init__(self, state_manager: StateManager, api_client: APIClient):
        super().__init__()
        self.state_manager = state_manager
        self.api_client = api_client
        
        self._timer = QTimer()
        self._timer.timeout.connect(self._capture_and_upload)
        self._is_active = False
        self._mss_instance = mss()
    
    def start(self):
        """Start screenshot service."""
        if self._is_active:
            return
        
        # Only start if screenshots are allowed
        if not self.state_manager.allow_screenshot:
            return
        
        # Only start when checked in
        if self.state_manager.state != AppState.CHECKED_IN:
            return
        
        self._is_active = True
        self._timer.start(SCREENSHOT_INTERVAL_SECONDS * 1000)  # Convert to milliseconds
    
    def stop(self):
        """Stop screenshot service."""
        if not self._is_active:
            return
        
        self._is_active = False
        self._timer.stop()
    
    def _capture_and_upload(self):
        """Capture screenshot and upload to API."""
        # Check if we should still be capturing
        if self.state_manager.state != AppState.CHECKED_IN:
            self.stop()
            return
        
        if not self.state_manager.allow_screenshot:
            self.stop()
            return
        
        try:
            # Capture full screen
            screenshot = self._mss_instance.grab(self._mss_instance.monitors[0])
            
            # Convert to PNG bytes (to_png is in mss.tools, not on MSS instance)
            png_bytes = to_png(screenshot.rgb, screenshot.size, output=None)
            
            # Encode to base64
            screenshot_base64 = base64.b64encode(png_bytes).decode('utf-8')
            
            # Upload to API
            self.api_client.upload_screenshot(screenshot_base64)
            
            self.screenshot_captured.emit()
        except Exception as e:
            print(f"Failed to capture/upload screenshot: {e}")
