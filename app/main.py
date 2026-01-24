"""
Main application entry point.
Wires together all components: UI, state management, API client, and background services.
"""
import sys
from datetime import datetime
from PySide6.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PySide6.QtCore import QTimer, Qt, QEvent
from PySide6.QtGui import QCloseEvent

from .api_client import APIClient


def _to_local_naive(dt: datetime):
    """Convert timezone-aware datetime to local naive for timer math."""
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt
from .state_manager import StateManager, AppState
from .activity_listener import ActivityListener
from .idle_tracker import IdleTracker
from .screenshot_service import ScreenshotService
from .ui.login_window import LoginWindow
from .ui.dashboard_window import DashboardWindow


class MinimizableStackedWidget(QStackedWidget):
    """Stacked widget that minimizes instead of closing."""
    
    def closeEvent(self, event: QCloseEvent):
        """Override close event to minimize instead of exit."""
        event.ignore()
        self.showMinimized()


class AttendanceApp:
    """Main application class."""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # Keep running when minimized
        
        # Core components
        self.api_client = APIClient()
        self.state_manager = StateManager()
        self.activity_listener = ActivityListener()
        self.idle_tracker = IdleTracker(
            self.state_manager, 
            self.api_client, 
            self.activity_listener
        )
        self.screenshot_service = ScreenshotService(
            self.state_manager,
            self.api_client
        )
        
        # UI components
        self.stacked_widget = MinimizableStackedWidget()
        self.login_window = LoginWindow()
        self.dashboard_window = DashboardWindow()
        
        self.stacked_widget.addWidget(self.login_window)
        self.stacked_widget.addWidget(self.dashboard_window)
        self.stacked_widget.setCurrentWidget(self.login_window)
        
        # Force break timer
        self._force_break_timer = QTimer()
        self._force_break_timer.timeout.connect(self._check_force_break)
        self._force_break_timer.start(5000)  # Check every 5 seconds
        
        # Wire up signals
        self._connect_signals()
        
        # Start activity listener
        self.activity_listener.start()
    
    def _connect_signals(self):
        """Connect all signals and slots."""
        # Login window
        self.login_window.login_requested.connect(self._handle_login)
        
        # Dashboard window
        self.dashboard_window.logout_requested.connect(self._handle_logout)
        self.dashboard_window.check_in_requested.connect(self._handle_check_in)
        self.dashboard_window.check_out_requested.connect(self._handle_check_out)
        self.dashboard_window.start_break_requested.connect(self._handle_start_break)
        self.dashboard_window.end_break_requested.connect(self._handle_end_break)
        
        # State manager
        self.state_manager.state_changed.connect(self._on_state_changed)
        self.state_manager.user_data_changed.connect(self._on_user_data_changed)
        
        # Activity listener (for resuming from force break)
        self.activity_listener.activity_detected.connect(self._on_activity_detected)
    
    def _handle_login(self, email: str, password: str, remember_me: bool):
        """Handle login request."""
        self.login_window.set_loading(True)
        QApplication.processEvents()
        try:
            result = self.api_client.login(email, password)
            
            session_token = result.get("session_token")
            if not session_token:
                raise Exception("Login successful but no session token received")
            
            staff_settings = result.get("staff_settings", {})
            company_rules = result.get("company_rules", {})
            # API returns "name" not "user_name"
            user_name = result.get("name", result.get("user_name", email.split("@")[0]))
            
            # Verify API client has the token
            if self.api_client.session_token != session_token:
                self.api_client.session_token = session_token
            
            # Update state manager
            self.state_manager.set_login_data(
                session_token,
                staff_settings,
                company_rules,
                user_name
            )
            
            # Switch to dashboard
            self.stacked_widget.setCurrentWidget(self.dashboard_window)
            self.dashboard_window.set_user_name(user_name)
            # Set shift from login staff_settings so it shows immediately
            ss = staff_settings or {}
            self.dashboard_window.set_shift_info(
                ss.get("shift_start", ""),
                ss.get("shift_end", ""),
                ss.get("timezone", "UTC")
            )
            # Fetch /staff/dashboard/stats to sync state (is_checked_in, on_break, today_attendance, etc.)
            self.dashboard_window.set_actions_loading(True)
            QApplication.processEvents()
            try:
                self._fetch_and_sync_dashboard()
            except Exception as e:
                print(f"Warning: Could not fetch dashboard stats: {e}")
            finally:
                self.dashboard_window.set_actions_loading(False)
            
        except Exception as e:
            self.login_window.show_error(str(e))
            QMessageBox.warning(
                self.login_window,
                "Login Failed",
                str(e)
            )
        finally:
            self.login_window.set_loading(False)
            self.dashboard_window.set_actions_loading(False)
    
    def _fetch_and_sync_dashboard(self):
        """Call GET /staff/dashboard/stats and sync state/UI from the response."""
        data = self.api_client.get_dashboard_stats()
        self._sync_state_from_dashboard_stats(data)

    def _sync_state_from_dashboard_stats(self, data: dict):
        """Sync state and UI from /staff/dashboard/stats.
        Uses: staff, today_attendance, today_sessions, is_checked_in, is_checked_out,
              on_break, current_break.
        - is_checked_out or (today_sessions empty and no today_attendance) -> Checked Out / Neutral
        - is_checked_in, on_break -> On Break (freeze timer)
        - is_checked_in, not on_break -> Checked In (running timer, late_by from today_attendance)
        """
        staff = data.get("staff") or {}
        today_attendance = data.get("today_attendance")
        is_checked_in = data.get("is_checked_in", False)
        is_checked_out = data.get("is_checked_out", False)
        on_break = data.get("on_break", False)
        current_break = data.get("current_break")

        self.state_manager.merge_staff_settings(staff)

        ss = self.state_manager.staff_settings or {}
        tz = staff.get("timezone") or ss.get("timezone") or "UTC"
        shift_start = staff.get("shift_start") or ss.get("shift_start") or ""
        shift_end = staff.get("shift_end") or ss.get("shift_end") or ""
        self.dashboard_window.set_shift_info(shift_start, shift_end, tz)

        if staff.get("name"):
            self.dashboard_window.set_user_name(staff["name"])

        if is_checked_out:
            self.state_manager.set_check_out()
            self.dashboard_window.set_was_checked_in(True)
            self.dashboard_window.reset_timer()
            self._refresh_dashboard_state()
            return

        if not is_checked_in:
            # Never checked in today (neutral)
            self.dashboard_window.set_was_checked_in(False)
            self.dashboard_window.reset_timer()
            self._refresh_dashboard_state()
            return

        # is_checked_in True
        check_in_iso = today_attendance.get("check_in") if today_attendance else None
        late_by_sec = today_attendance.get("late_by") if today_attendance else None
        late_by_minutes = (
            (int(late_by_sec) + 30) // 60
            if (late_by_sec is not None and isinstance(late_by_sec, (int, float)) and late_by_sec > 0)
            else None
        )

        check_in_timestamp = None
        check_in_time_str = None
        if check_in_iso:
            try:
                check_in_timestamp = datetime.fromisoformat(check_in_iso.replace("Z", "+00:00"))
                check_in_timestamp = _to_local_naive(check_in_timestamp)
                check_in_time_str = check_in_timestamp.strftime("%H:%M")
            except Exception as e:
                print(f"Error parsing check_in: {e}")
                check_in_time_str = check_in_iso[:5] if len(str(check_in_iso)) >= 5 else datetime.now().strftime("%H:%M")
                check_in_timestamp = datetime.now()
        else:
            check_in_time_str = datetime.now().strftime("%H:%M")
            check_in_timestamp = datetime.now()

        if on_break:
            break_start_timestamp = None
            break_time_str = None
            start_iso = None
            if isinstance(current_break, dict) and current_break.get("start"):
                start_iso = current_break["start"]
            elif (today_attendance or {}).get("breaks"):
                for b in (today_attendance.get("breaks") or []):
                    if isinstance(b, dict) and b.get("start") and not b.get("end"):
                        start_iso = b["start"]
                        break
            if start_iso:
                try:
                    break_start_timestamp = datetime.fromisoformat(str(start_iso).replace("Z", "+00:00"))
                    break_start_timestamp = _to_local_naive(break_start_timestamp)
                    break_time_str = break_start_timestamp.strftime("%H:%M")
                except Exception as e:
                    print(f"Error parsing break start: {e}")
            if not break_time_str or break_start_timestamp is None:
                break_time_str = datetime.now().strftime("%H:%M")
                break_start_timestamp = datetime.now()

            self.state_manager.set_break_start(break_time_str, is_force=False)
            self.dashboard_window.set_check_in_time(
                check_in_time_str=check_in_time_str,
                check_in_timestamp=check_in_timestamp,
                break_start_timestamp=break_start_timestamp,
            )
            self._refresh_dashboard_state()
            return

        # Checked in, not on break
        self.state_manager.set_check_in(check_in_time_str, late_by_minutes)
        self.dashboard_window.set_check_in_time(
            check_in_time_str=check_in_time_str,
            check_in_timestamp=check_in_timestamp,
            break_start_timestamp=None,
        )
        self._refresh_dashboard_state()
    
    def _handle_logout(self):
        """Handle logout request."""
        try:
            # Stop all services
            self.idle_tracker.stop()
            self.screenshot_service.stop()
            
            # Logout from API (may fail if already logged out, but that's okay)
            try:
                self.api_client.logout()
            except Exception as e:
                print(f"Logout API call failed (may already be logged out): {e}")
            
            # Clear state
            self.state_manager.logout()
            
            # Clear login fields
            self.login_window.clear_fields()
            
            # Switch to login
            self.stacked_widget.setCurrentWidget(self.login_window)
            
        except Exception as e:
            print(f"Logout error: {e}")
            # Still clear local state even if API call fails
            self.state_manager.logout()
            self.login_window.clear_fields()
            self.stacked_widget.setCurrentWidget(self.login_window)
    
    def _handle_check_in(self):
        """Handle check-in request."""
        if not self.api_client.session_token:
            QMessageBox.warning(
                self.dashboard_window,
                "Check-in Failed",
                "Not authenticated. Please login again."
            )
            return

        self.dashboard_window.set_actions_loading(True)
        QApplication.processEvents()
        try:
            self.api_client.check_in()
            try:
                self._fetch_and_sync_dashboard()
            except Exception as e:
                print(f"Dashboard stats after check-in: {e}")
        except Exception as e:
            QMessageBox.warning(
                self.dashboard_window,
                "Check-in Failed",
                str(e)
            )
        finally:
            self.dashboard_window.set_actions_loading(False)
            self._refresh_dashboard_state()
    
    def _handle_check_out(self):
        """Handle check-out request."""
        self.dashboard_window.set_actions_loading(True)
        QApplication.processEvents()
        try:
            self.api_client.check_out()
            try:
                self._fetch_and_sync_dashboard()
            except Exception as e:
                print(f"Dashboard stats after check-out: {e}")
                self.state_manager.set_check_out()
                self.dashboard_window.set_was_checked_in(True)
                self.dashboard_window.reset_timer()
        except Exception as e:
            QMessageBox.warning(
                self.dashboard_window,
                "Check-out Failed",
                str(e)
            )
        finally:
            self.dashboard_window.set_actions_loading(False)
            self._refresh_dashboard_state()
    
    def _handle_start_break(self):
        """Handle start break request."""
        self.dashboard_window.set_actions_loading(True)
        QApplication.processEvents()
        try:
            self.api_client.start_break()
            self._fetch_and_sync_dashboard()
        except Exception as e:
            QMessageBox.warning(
                self.dashboard_window,
                "Break Failed",
                str(e)
            )
        finally:
            self.dashboard_window.set_actions_loading(False)
            self._refresh_dashboard_state()
    
    def _handle_end_break(self):
        """Handle end break request."""
        self.dashboard_window.set_actions_loading(True)
        QApplication.processEvents()
        try:
            self.api_client.end_break()
            self._fetch_and_sync_dashboard()
        except Exception as e:
            QMessageBox.warning(
                self.dashboard_window,
                "Break Failed",
                str(e)
            )
        finally:
            self.dashboard_window.set_actions_loading(False)
            self._refresh_dashboard_state()
    
    def _on_state_changed(self, new_state: AppState):
        """Handle state change."""
        # Update UI
        self.dashboard_window.update_state(
            new_state,
            self.state_manager.check_in_time,
            self.state_manager.break_start_time,
            self.state_manager.late_by_minutes
        )
        
        # Manage background services based on state
        if new_state == AppState.CHECKED_IN:
            # Start idle tracking
            self.idle_tracker.start()
            
            # Start screenshots if allowed
            if self.state_manager.allow_screenshot:
                self.screenshot_service.start()
            else:
                self.screenshot_service.stop()
        
        elif new_state == AppState.ON_BREAK:
            # Stop services
            self.idle_tracker.stop()
            self.screenshot_service.stop()
        
        elif new_state == AppState.FORCE_BREAK:
            # Stop services
            self.idle_tracker.stop()
            self.screenshot_service.stop()
        
        elif new_state == AppState.LOGGED_OUT:
            # Stop all services
            self.idle_tracker.stop()
            self.screenshot_service.stop()
    
    def _on_user_data_changed(self, user_data: dict):
        """Handle user data change."""
        # Update dashboard with user name if needed
        if "user_name" in user_data:
            self.dashboard_window.set_user_name(user_data["user_name"])
    
    def _refresh_dashboard_state(self):
        """Re-apply dashboard UI from current state (e.g. after clearing loading)."""
        self.dashboard_window.update_state(
            self.state_manager.state,
            self.state_manager.check_in_time,
            self.state_manager.break_start_time,
            self.state_manager.late_by_minutes
        )
    
    def _check_force_break(self):
        """Every 5s: fetch /staff/dashboard/stats when on dashboard and logged in; then check force break."""
        if self.api_client.session_token and self.stacked_widget.currentWidget() == self.dashboard_window:
            try:
                self._fetch_and_sync_dashboard()
            except Exception as e:
                print(f"Dashboard stats poll: {e}")

        # Only check force break when checked in
        if self.state_manager.state != AppState.CHECKED_IN:
            return

        # Calculate idle time
        last_activity = self.activity_listener.get_last_activity_time()
        now = datetime.now()
        idle_seconds = int((now - last_activity).total_seconds())
        
        # Check if force break threshold reached
        force_break_time = self.state_manager.force_break_time
        if idle_seconds >= force_break_time:
            try:
                # Trigger force break
                self.api_client.force_break_start()
                break_start_time = datetime.now().strftime("%H:%M")
                self.state_manager.set_break_start(break_start_time, is_force=True)
                # Freeze timer on force break too
                self.dashboard_window.set_break_freeze(datetime.now())
            except Exception as e:
                print(f"Failed to trigger force break: {e}")
    
    def _on_activity_detected(self):
        """Handle activity detection (for resuming from force break)."""
        # If in force break, end it on any activity
        if self.state_manager.state == AppState.FORCE_BREAK:
            try:
                self.api_client.end_break()
                self.state_manager.set_break_end()
            except Exception as e:
                print(f"Failed to end force break: {e}")
    
    def run(self):
        """Run the application."""
        self.stacked_widget.show()
        return self.app.exec()


def main():
    """Entry point."""
    app = AttendanceApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
