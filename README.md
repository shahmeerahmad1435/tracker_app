# Attendance Tracker Desktop Application

A cross-platform desktop attendance and monitoring agent built with Python and PySide6.

## Features

- **User Authentication**: Login with email and password
- **Check-in/Check-out**: Track work hours
- **Manual Break**: Start and end breaks manually
- **Force Break**: Automatic break triggered by idle time
- **Idle Tracking**: Monitor keyboard and mouse activity
- **Screenshot Capture**: Periodic full-screen screenshots (when enabled)
- **Background Monitoring**: Continuous monitoring while app runs

## Requirements

- Python 3.11+
- PySide6
- requests or httpx
- mss (for screenshots)
- pynput (for activity detection)

## Installation

1. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set API base URL (optional, defaults to `http://localhost:8000/api`):
```bash
export API_BASE_URL="https://your-api-url.com/api"
```

## Usage

1. Activate the virtual environment (if not already activated):
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Run the application:
```bash
python main.py
```

**Note:** On macOS, if you get a "command not found: pip" error, use `python3 -m pip` instead, or use a virtual environment as shown above.

## API Endpoints

The application expects the following REST API endpoints:

- `POST /auth/login` - User authentication
- `POST /staff/check-in` - Check in
- `POST /staff/check-out` - Check out
- `POST /staff/break/start` - Start manual break
- `POST /staff/break/end` - End break
- `POST /desktop/break/force-start` - Force break (idle-based)
- `POST /desktop/idle/report` - Report idle time
- `POST /desktop/screenshot/upload` - Upload screenshot

## Application States

- **LOGGED_OUT**: User not checked in
- **CHECKED_IN**: User checked in and working
- **ON_BREAK**: User on manual break
- **FORCE_BREAK**: User on automatic break (idle-based)

## Window Behavior

- **Close (X) button**: Minimizes the application (does not exit)
- **Logout button**: Returns to login screen and clears session
- Application continues running in background when minimized

## Resilience

- **Foreground / background**: The app keeps running whether in the foreground or minimized; closing the window only minimizes it.
- **Internet disconnect / reconnect**: If the connection is lost, background API calls (idle report, screenshots, force break, dashboard sync) fail safely and are retried on the next timer tick. When the connection is restored, the next scheduled call succeeds; the app does not need to be restarted.

## Project Structure

```
/app
 ├── main.py                 # Application entry point
 ├── api_client.py           # REST API client
 ├── state_manager.py        # State management
 ├── idle_tracker.py        # Idle time tracking
 ├── screenshot_service.py   # Screenshot capture
 ├── activity_listener.py    # Keyboard/mouse activity
 ├── config.py              # Configuration
 └── ui/
     ├── login_window.py     # Login UI
     └── dashboard_window.py # Dashboard UI
```

## Building for Windows (installer for clients)

To create a Windows `.exe` and installer to share with clients, use a **Windows machine** and follow **[BUILD_WINDOWS.md](BUILD_WINDOWS.md)**. You will get:

- **`dist\AttendanceTracker.exe`** — portable executable (zip and send), or  
- **`installer_output\AttendanceTracker_Setup_1.0.0.exe`** — installer (after building with Inno Setup).

## Notes

- All state is stored in memory (no database)
- Session token and settings are cleared on logout
- Screenshots are only captured when `allow_screenshot == "yes"` in staff settings
- Force break time is configured via company rules from API
