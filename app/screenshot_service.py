"""
Screenshot capture service.
Captures full-screen screenshots, compresses (resize + JPEG), and uploads to API.
"""
import base64
import io
from PySide6.QtCore import QObject, Signal, QTimer
from mss import mss
from PIL import Image
from .state_manager import StateManager, AppState
from .api_client import APIClient

# Compress to reduce payload size and avoid timeouts / "entity too large"
MAX_DIMENSION = 1280   # max width or height (keeps aspect ratio)
JPEG_QUALITY = 75      # 1-95; lower = smaller file


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
        # API sends screenshot_interval in minutes; state_manager gives seconds
        interval_ms = self.state_manager.screenshot_interval_seconds * 1000
        self._timer.start(int(interval_ms))
    
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
            w, h = screenshot.size

            # Build PIL Image from mss RGB bytes
            img = Image.frombytes("RGB", (w, h), screenshot.rgb)

            # Resize if larger than MAX_DIMENSION to reduce size
            if w > MAX_DIMENSION or h > MAX_DIMENSION:
                resample = getattr(Image, "Resampling", Image).LANCZOS
                img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), resample)

            # Compress as JPEG (much smaller than PNG)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            jpeg_bytes = buf.getvalue()

            screenshot_base64 = base64.b64encode(jpeg_bytes).decode("utf-8")

            # Upload to API (uses longer timeout)
            self.api_client.upload_screenshot(screenshot_base64)

            self.screenshot_captured.emit()
        except Exception as e:
            print(f"Failed to capture/upload screenshot: {e}")
