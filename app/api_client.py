"""
REST API client for attendance tracking application.
Handles all API communication with the backend.
"""
import requests
import json
from datetime import datetime
from typing import Dict, Optional, Any
from .config import API_BASE_URL


def _extract_error_message(response, fallback_exc) -> str:
    """Extract user-friendly error message from API response JSON."""
    try:
        error_data = response.json()
        print(f"[DEBUG] Error Response: {json.dumps(error_data, indent=2)}")
        if isinstance(error_data, dict):
            detail = error_data.get("detail", error_data.get("message", error_data.get("error")))
            if isinstance(detail, str) and detail:
                return detail
            if isinstance(detail, list) and detail and isinstance(detail[0], dict):
                msg = detail[0].get("msg", detail[0].get("loc", str(detail[0])))
                return str(msg) if msg else str(detail[0])
            if detail is not None:
                return str(detail)
    except Exception:
        print(f"[DEBUG] Error Response (text): {response.text[:500]}")
    return str(fallback_exc)


class APIClient:
    """Client for making REST API calls."""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.session_token: Optional[str] = None
        self.session = requests.Session()
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with session token if available."""
        headers = {"Content-Type": "application/json"}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        return headers
    
    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Make a GET request."""
        url = f"{self.base_url}{endpoint}"
        headers = self._headers()
        
        # Debug logging
        print(f"[DEBUG] GET {url}")
        print(f"[DEBUG] Headers: {json.dumps({k: v if k != 'Authorization' else 'Bearer ***' for k, v in headers.items()}, indent=2)}")
        
        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=10
            )
            
            print(f"[DEBUG] Response Status: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise Exception(_extract_error_message(response, e))
        except requests.exceptions.RequestException as e:
            raise Exception(str(e))
    
    def _post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a POST request."""
        url = f"{self.base_url}{endpoint}"
        headers = self._headers()
        
        # Debug logging (can be removed in production)
        print(f"[DEBUG] POST {url}")
        print(f"[DEBUG] Headers: {json.dumps({k: v if k != 'Authorization' else 'Bearer ***' for k, v in headers.items()}, indent=2)}")
        if data:
            print(f"[DEBUG] Body: {json.dumps(data, indent=2)}")
        
        try:
            response = self.session.post(
                url,
                json=data,
                headers=headers,
                timeout=10
            )
            
            # Debug response
            print(f"[DEBUG] Response Status: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            user_msg = _extract_error_message(response, e)
            raise Exception(user_msg)
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        POST /auth/login
        Returns: {session_token, staff_settings, company_rules}
        """
        data = {"email": email, "password": password}
        result = self._post("/auth/login", data)
        self.session_token = result.get("session_token")
        return result
    
    def check_in(self) -> Dict[str, Any]:
        """
        POST /staff/check-in
        Returns: {status, check_in_time, ...}
        """
        if not self.session_token:
            raise Exception("Not authenticated. Please login first.")
        return self._post("/staff/check-in")
    
    def check_out(self) -> Dict[str, Any]:
        """
        POST /staff/check-out
        Returns: {status, ...}
        """
        return self._post("/staff/check-out")
    
    def start_break(self) -> Dict[str, Any]:
        """
        POST /staff/break/start
        Returns: {status, break_start_time, ...}
        """
        return self._post("/staff/break/start")
    
    def end_break(self) -> Dict[str, Any]:
        """
        POST /staff/break/end
        Returns: {status, ...}
        """
        return self._post("/staff/break/end")
    
    def force_break_start(self) -> Dict[str, Any]:
        """
        POST /desktop/break/force-start
        Returns: {status, ...}
        """
        return self._post("/desktop/break/force-start")
    
    def report_idle(self, idle_seconds: int) -> Dict[str, Any]:
        """
        POST /desktop/idle/report
        Body: {idle_seconds: int, timestamp: str (ISO format)}
        Returns: {status, ...}
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        data = {
            "idle_seconds": idle_seconds,
            "timestamp": timestamp
        }
        return self._post("/desktop/idle/report", data)
    
    def upload_screenshot(self, screenshot_base64: str) -> Dict[str, Any]:
        """
        POST /desktop/screenshot/upload
        Body: {screenshot_base64: str, timestamp: str (ISO format)}
        Returns: {status, ...}
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        data = {
            "screenshot_base64": screenshot_base64,
             "screen_status": "active",
            "timestamp": timestamp
        }
        return self._post("/desktop/screenshot/upload", data)
    
    def logout(self) -> Dict[str, Any]:
        """
        POST /auth/logout
        Logout and invalidate session
        Returns: {status, ...}
        """
        try:
            result = self._post("/auth/logout")
            self.session_token = None
            return result
        except Exception:
            # Even if logout fails, clear the token locally
            self.session_token = None
            return {}
    
    def get_current_user(self) -> Dict[str, Any]:
        """
        GET /auth/me
        Get current logged-in user information
        Returns: {user info}
        """
        return self._get("/auth/me")
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        GET /staff/dashboard/stats
        Returns: staff, today_attendance, today_sessions, is_checked_in, is_checked_out,
                 on_break, current_break, stats, etc.
        """
        return self._get("/staff/dashboard/stats")

    def get_attendance_status(self) -> Dict[str, Any]:
        """
        GET /desktop/attendance/status
        Get current attendance status including check-in time, break status, work duration
        Returns: {status, check_in_time, break_status, ...}
        """
        return self._get("/desktop/attendance/status")
