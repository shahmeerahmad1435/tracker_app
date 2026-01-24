# Building the Windows Installer for Attendance Tracker

---

## Option C: GitHub Actions (build from Mac — no Windows needed)

**Free** for public repos. For private repos: 2,000 minutes/month free (each build ~3–5 min).

1. **Push your code to GitHub** (create a repo if needed).
2. Open the repo → **Actions** tab → workflow **"Build Windows exe"**.
3. Click **"Run workflow"** → **"Run workflow"** (or it runs automatically on push to `main`/`master`).
4. When it finishes (green ✓), open the run → **Artifacts** → download **`AttendanceTracker-Windows`** (a zip with `AttendanceTracker.exe`).

Send the `.exe` to your client. No Windows PC required.

---

## Option A: Quick build on a Windows PC (portable .exe only)

For a single **portable** `AttendanceTracker.exe` that you can zip and send to your client:

### 1. On a Windows machine

- Install **Python 3.10 or 3.11** (64-bit): https://www.python.org/downloads/  
  - During setup, enable **“Add Python to PATH”**.

### 2. Open Command Prompt or PowerShell in the project folder

```cmd
cd C:\path\to\tracker_app
```

### 3. Create a virtual environment and install dependencies

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

### 4. Build the .exe

```cmd
pyinstaller --noconfirm --clean AttendanceTracker.spec
```

### 5. Result

- **`dist\AttendanceTracker.exe`** — single executable, no install needed.
- Zip `AttendanceTracker.exe` and send it to your client.
- They unzip, double‑click `AttendanceTracker.exe` to run.

---

## Option B: Full installer (recommended for clients)

Builds the same .exe, then packages it into an installer (Start Menu shortcut, optional Desktop icon, Uninstall).

### 1–4. Same as Option A

(Install Python, venv, deps, and run `pyinstaller --noconfirm --clean AttendanceTracker.spec`.)

### 5. Install Inno Setup 6

- Download: https://jrsoftware.org/isinfo.php  
- Run the installer (default options are fine).

### 6. Create the installer

**Using the Inno Setup GUI**

1. Open **Inno Setup Compiler**.
2. **File → Open** → select `installer.iss` from the project folder.
3. **Build → Compile** (or press Ctrl+F9).

**Using the command line**

```cmd
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

### 7. Result

- **`installer_output\AttendanceTracker_Setup_1.0.0.exe`** — this is the installer to share.
- Your client runs it to install the app, then launches it from the Start Menu or Desktop shortcut.

---

## What to send your client

| File | Use case |
|------|----------|
| **`dist\AttendanceTracker.exe`** | Portable: no install, unzip and run. |
| **`installer_output\AttendanceTracker_Setup_1.0.0.exe`** | Installer: install to Program Files, Start Menu, Uninstall support. |

---

## Using the batch script

From the project root (with `venv` activated and dependencies installed):

```cmd
build_windows.bat
```

This will:

1. Install PyInstaller if needed  
2. Run `pyinstaller` with `AttendanceTracker.spec`  
3. Print where the .exe and installer are

You still need to run Inno Setup (Step 6 above) if you want the full installer.

---

## Troubleshooting

### “Python not found” / “pyinstaller not found”

- Ensure Python is on PATH and the venv is activated:  
  `venv\Scripts\activate`
- Reinstall PyInstaller:  
  `pip install pyinstaller`

### App fails to start (black window, then closes)

- First, run from a console to see errors:

  ```cmd
  dist\AttendanceTracker.exe
  ```

- If you see missing DLL or Qt/platform errors, try rebuilding with a clean cache:

  ```cmd
  pyinstaller --noconfirm --clean AttendanceTracker.spec
  ```

### Antivirus or SmartScreen

- The .exe is not signed, so SmartScreen or antivirus may warn. The client can:
  - Use “More info” → “Run anyway” (SmartScreen), or  
  - Add an exception for the .exe or folder.  
- For production, sign the .exe and/or the installer with a code‑signing certificate.

### Build on CI

See **Option C** above for the ready-made GitHub Actions workflow.

---

## Summary

1. Build on **Windows** (Python 3.10/3.11, 64‑bit recommended).  
2. `pip install -r requirements.txt pyinstaller`  
3. `pyinstaller --noconfirm --clean AttendanceTracker.spec`  
4. Share **`dist\AttendanceTracker.exe`** (portable) and/or **`installer_output\AttendanceTracker_Setup_1.0.0.exe`** (after building with Inno Setup).
