@echo off
REM Build Attendance Tracker for Windows
REM Run this on a Windows machine from the project root.

echo [1/3] Installing build dependencies...
pip install pyinstaller -q

echo [2/3] Building .exe with PyInstaller...
pyinstaller --noconfirm --clean AttendanceTracker.spec
if errorlevel 1 (
    echo PyInstaller build failed.
    exit /b 1
)

echo [3/3] Done. Output: dist\AttendanceTracker.exe
echo.
echo To create an installer:
echo   1. Install Inno Setup 6: https://jrsoftware.org/isinfo.php
echo   2. Open installer.iss in Inno Setup and compile (or run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
echo   3. Installer will be in: installer_output\AttendanceTracker_Setup_1.0.0.exe
echo.
echo To share with your client: send dist\AttendanceTracker.exe (portable) or the installer .exe from installer_output\
pause
