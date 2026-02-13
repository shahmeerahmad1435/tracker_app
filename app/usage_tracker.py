"""
Usage tracker: when usage_policy_enabled, samples active app (and browser URL) and reports to POST /desktop/usage/report.
"""
from typing import Dict, Tuple, Any, Optional
from PySide6.QtCore import QObject, QTimer
from .state_manager import StateManager, AppState
from .api_client import APIClient
from .usage_helper import get_active_app_and_url


SAMPLE_INTERVAL_MS = 10_000   # Sample every 10 seconds
REPORT_INTERVAL_MS = 1 * 60 * 1000  # Report every 5 minutes


class UsageTracker(QObject):
    """Tracks app/website usage and reports to API when usage_policy_enabled and checked in."""

    def __init__(self, state_manager: StateManager, api_client: APIClient):
        super().__init__()
        self.state_manager = state_manager
        self.api_client = api_client
        self._sample_timer = QTimer()
        self._sample_timer.timeout.connect(self._sample)
        self._report_timer = QTimer()
        self._report_timer.timeout.connect(self._report)
        self._accumulated: Dict[Tuple[str, Optional[str]], int] = {}  # (app_name, site_url or "") -> seconds
        self._is_active = False

    def start(self):
        if self._is_active:
            return
        if not self.state_manager.usage_policy_enabled:
            return
        if self.state_manager.state != AppState.CHECKED_IN:
            return
        self._is_active = True
        self._accumulated.clear()
        self._sample_timer.start(SAMPLE_INTERVAL_MS)
        self._report_timer.start(REPORT_INTERVAL_MS)

    def stop(self):
        if not self._is_active:
            return
        self._is_active = False
        self._sample_timer.stop()
        self._report_timer.stop()
        self._report()  # Flush remaining
        self._accumulated.clear()

    def _sample(self):
        if self.state_manager.state != AppState.CHECKED_IN:
            self.stop()
            return
        if not self.state_manager.usage_policy_enabled:
            self.stop()
            return
        app_name, site_url = get_active_app_and_url()
        if not app_name:
            return
        key = (app_name, site_url or "")
        self._accumulated[key] = self._accumulated.get(key, 0) + (SAMPLE_INTERVAL_MS // 1000)

    def _report(self):
        if not self._accumulated:
            return
        entries = []
        for (app_name, site_url), duration_seconds in self._accumulated.items():
            if duration_seconds <= 0:
                continue
            entry = {"app_name": app_name, "duration_seconds": duration_seconds}
            if site_url:
                entry["site_url"] = site_url
            entries.append(entry)
        self._accumulated.clear()
        if not entries:
            return
        try:
            self.api_client.report_usage(entries)
        except Exception as e:
            print(f"Failed to report usage: {e}")
            # Re-accumulate so we don't lose data (optional: could drop)
            for ent in entries:
                key = (ent["app_name"], ent.get("site_url") or "")
                self._accumulated[key] = self._accumulated.get(key, 0) + ent["duration_seconds"]
