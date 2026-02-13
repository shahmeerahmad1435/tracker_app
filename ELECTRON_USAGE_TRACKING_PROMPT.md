# How usage tracking works in this project (Python/PySide6)

## Overview

When **usage_policy_enabled** is true in staff settings (from login/API) and the user is **CHECKED_IN**, the app:

1. **Samples** the currently active (frontmost) application every **10 seconds**.
2. For **browsers**, also gets the **active tab URL** when possible (macOS: AppleScript; Windows: not implemented).
3. **Accumulates** time per `(app_name, site_url)` — each sample adds 10 seconds to that key.
4. **Reports** accumulated entries to the API every **1 minute** via `POST /desktop/usage/report`, then clears the buffer. If the API call fails, the entries are re-accumulated so we don’t lose data.

So the backend receives: **how many seconds** the user spent in each **app**, and for browsers **which site (URL)** they were on.

---

## Data flow

- **usage_policy_enabled**: From `staff_settings.usage_policy_enabled` (login + dashboard sync). Tracker runs only when this is true and state is CHECKED_IN.
- **Sampling**: Every 10 s → `get_active_app_and_url()` → `(app_name, site_url)`.
- **Accumulation**: `(app_name, site_url or "")` → add 10 seconds.
- **Report**: Every 60 s → build `entries: [{ app_name, duration_seconds, site_url? }]` → `POST /desktop/usage/report` with `{ "entries": entries }`, Authorization: Bearer &lt;session_token&gt;.

---

## Getting active app and browser URL

- **macOS**
  - **Active app**: `osascript -e 'tell application "System Events" to get name of first process whose frontmost is true'`
  - **Browser URL** (only when app is a known browser): AppleScript per app, e.g.  
    Chrome: `tell application "Google Chrome" to get URL of active tab of front window`  
    Safari: `tell application "Safari" to get URL of current tab of front window`  
    Edge: `tell application "Microsoft Edge" to get URL of active tab of front window`  
    Brave: `tell application "Brave Browser" to get URL of active tab of front window`  
    Firefox: not supported (AppleScript limited).
- **Windows**
  - **Active app**: `GetForegroundWindow` → `GetWindowThreadProcessId` → process name (e.g. via psutil). Strip `.exe` from name.
  - **Browser URL**: Not implemented (would require UIA/accessibility).

---

## API

- **Endpoint**: `POST /desktop/usage/report`
- **Headers**: `Content-Type: application/json`, `Authorization: Bearer <session_token>`
- **Body**: `{ "entries": [ { "app_name": string, "duration_seconds": number, "site_url"?: string } ] }`
- **When**: Only when user is checked in and `usage_policy_enabled` is true. Stop on check-out, break, force break, or when policy is disabled.

---

## Lifecycle

- **Start**: When transitioning to CHECKED_IN and `usage_policy_enabled` is true (e.g. after check-in or after dashboard sync that sets staff settings).
- **Stop**: On logout, check-out, start break, force break, or when `usage_policy_enabled` becomes false. On stop, flush remaining accumulated data with one last report.

---


# PROMPT TO PASTE IN ELECTRON PROJECT

Copy everything below this line and paste it into your Electron project (e.g. as a prompt for the AI or as a spec for a developer).

---

Implement **usage tracking** in this Electron app so we report how much time the user spent in each application and, for browsers, which tab/site they were on. Match the behavior below.

## Requirements

1. **When to run**
   - Only when the user is **checked in** (your app’s “checked in” state).
   - Only when **usage_policy_enabled** is true in staff settings (from login or dashboard sync API). If you don’t have staff settings yet, add a flag that can be set from the API response (e.g. `staff_settings.usage_policy_enabled`).
   - Stop when user checks out, goes on break, force break, or logs out. Also stop when `usage_policy_enabled` becomes false.

2. **Sampling**
   - Every **10 seconds**, determine the currently active (frontmost) application and, if it’s a browser, the active tab URL.
   - Treat each 10-second interval as **10 seconds** of usage for that `(app_name, site_url)`.
   - **Accumulate** in memory: key = `(app_name, site_url or "")`, value = total seconds. So multiple 10-second samples in the same app (and same site for browsers) add up.

3. **Reporting**
   - Every **1 minute**, send the accumulated usage to the API in one request, then clear the buffer.
   - **Endpoint**: `POST /desktop/usage/report`
   - **Headers**: `Content-Type: application/json`, `Authorization: Bearer <session_token>` (use the same session token as for other API calls).
   - **Body**: `{ "entries": [ { "app_name": string, "duration_seconds": number, "site_url"?: string } ] }`
   - **Rules**: Include `site_url` only when the entry is for a browser and we have the tab URL; otherwise omit it. If the request fails, keep the entries in the buffer and retry on the next report cycle (do not drop them).

4. **Getting active app and browser URL**
   - **macOS**
     - **Active app**: Run AppleScript from the main process (e.g. `child_process.execSync` or `exec`):  
       `osascript -e 'tell application "System Events" to get name of first process whose frontmost is true'`  
       Use the trimmed stdout as the app name.
     - **Browser URL** (only when the frontmost app is a known browser): Run app-specific AppleScript, for example:
       - Google Chrome / Chromium: `tell application "Google Chrome" to get URL of active tab of front window`
       - Microsoft Edge: `tell application "Microsoft Edge" to get URL of active tab of front window`
       - Safari: `tell application "Safari" to get URL of current tab of front window`
       - Brave: `tell application "Brave Browser" to get URL of active tab of front window`
       - Firefox: skip URL (AppleScript support is limited).
     - Consider a list of known browser app names (e.g. "Google Chrome", "Chromium", "Microsoft Edge", "Safari", "Firefox", "Brave Browser") and only try to get URL for those.
   - **Windows**
     - **Active app**: Get the foreground window’s process name (e.g. via `GetForegroundWindow` + `GetWindowThreadProcessId` + get process name). Use a native addon, `ffi-napi`, or an npm package that exposes this. Strip `.exe` from the process name for display.
     - **Browser URL**: Optional for now (our reference app doesn’t implement it on Windows; would require UIA/accessibility). You can send `app_name` and `duration_seconds` without `site_url` for browsers on Windows.

5. **Lifecycle**
   - Start the usage tracker when: user becomes checked in **and** `usage_policy_enabled` is true (e.g. after check-in or after fetching dashboard/staff settings that set this flag).
   - Stop the tracker on: check-out, start break, force break, logout, or when `usage_policy_enabled` is false. On stop, perform one final report with any remaining accumulated entries so no data is lost.

6. **Implementation notes**
   - Run sampling and reporting timers in the **main process** (Node), not in the renderer, so they keep running when the window is hidden or minimized.
   - Use the same API base URL and session token as the rest of the app. If the app uses a dedicated API module, add a `reportUsage(entries)` (or similar) that POSTs to `/desktop/usage/report` with the body and auth above.

Implement this so the backend receives the same semantics: per-app and per-browser-tab (when available) time spent in seconds, reported every minute while the user is checked in and usage policy is enabled.
