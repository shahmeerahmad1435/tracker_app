"""
Platform-specific helpers to get active application name and (for browsers) current site URL.
Used when usage_policy_enabled to report app/website usage to POST /desktop/usage/report.
"""
import sys
import subprocess
from typing import Tuple, Optional


# Known browser bundle names (macOS) / process names (Windows) so we can try to get URL
BROWSER_APPS = frozenset({"Google Chrome", "Chromium", "Microsoft Edge", "Safari", "Firefox", "Brave Browser"})


def get_active_app_and_url() -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (app_name, site_url or None).
    site_url is set only for browser apps when we can get the active tab URL.
    """
    if sys.platform == "darwin":
        return _get_active_app_and_url_macos()
    if sys.platform == "win32":
        return _get_active_app_and_url_windows()
    return (None, None)


def _get_active_app_and_url_macos() -> Tuple[Optional[str], Optional[str]]:
    try:
        out = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
            capture_output=True, text=True, timeout=2
        )
        if out.returncode != 0 or not out.stdout:
            return (None, None)
        app_name = out.stdout.strip()
        if not app_name:
            return (None, None)
        site_url = None
        if app_name in BROWSER_APPS:
            site_url = _get_browser_url_macos(app_name)
        return (app_name, site_url)
    except Exception:
        return (None, None)


def _get_browser_url_macos(app_name: str) -> Optional[str]:
    """Get active tab URL for Chrome/Safari/Edge on macOS via AppleScript."""
    script = None
    if app_name == "Google Chrome" or app_name == "Chromium":
        script = 'tell application "Google Chrome" to get URL of active tab of front window'
    elif app_name == "Microsoft Edge":
        script = 'tell application "Microsoft Edge" to get URL of active tab of front window'
    elif app_name == "Safari":
        script = 'tell application "Safari" to get URL of current tab of front window'
    elif app_name == "Brave Browser":
        script = 'tell application "Brave Browser" to get URL of active tab of front window'
    elif app_name == "Firefox":
        # Firefox AppleScript support is limited; skip URL
        return None
    if not script:
        return None
    try:
        out = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
        if out.returncode == 0 and out.stdout and out.stdout.strip():
            url = out.stdout.strip()
            if url and url != "missing value":
                return url
    except Exception:
        pass
    return None


def _get_active_app_and_url_windows() -> Tuple[Optional[str], Optional[str]]:
    """Get foreground window process name on Windows. Browser URL not implemented (would need UIA/accessibility)."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        pid = wintypes.DWORD()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return (None, None)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            import psutil
            proc = psutil.Process(pid.value)
            name = proc.name()
            if name:
                # .exe strip
                if name.lower().endswith(".exe"):
                    name = name[:-4]
                site_url = None
                if any(b in name for b in ("chrome", "msedge", "firefox", "safari", "brave")):
                    site_url = None  # Windows: would need UIA to get URL
                return (name, site_url)
        except Exception:
            pass
        return (None, None)
    except Exception:
        return (None, None)
