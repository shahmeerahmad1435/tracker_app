"""
Configuration settings for the attendance tracking application.
"""
import os

# API Configuration
# API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
API_BASE_URL = os.getenv("API_BASE_URL", "https://workforce-hub-180.preview.emergentagent.com/api")

# Application Settings
APP_NAME = "Attendance Tracker"
APP_VERSION = "1.0.0"

# Screenshot Settings
SCREENSHOT_INTERVAL_SECONDS = 10  # Default interval, can be overridden by API

# Idle Tracking Settings
IDLE_CHECK_INTERVAL_SECONDS = 5  # How often to check for idle time

# UI Settings
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
WINDOW_BORDER_RADIUS = 25

# Colors (matching the UI design)
COLOR_PRIMARY = "#6A5ACD"  # Blue/Purple for active buttons (slate blue)
COLOR_SUCCESS = "#63d14c"  # Green for "Checked In"
COLOR_ALERT = "#ea3323"    # Red for "On Break" / "Force Break"
COLOR_TEXT_DARK = "#333333"
COLOR_TEXT_LIGHT = "#666666"
COLOR_BACKGROUND = "#ffffff"  # White for card
COLOR_BACKGROUND_DARK = "#555555"  # Dark grey background
COLOR_BORDER_LIGHT = "#D3D3D3"  # Light grey for borders
