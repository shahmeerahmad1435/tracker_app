# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Attendance Tracker (Windows)
# Run on Windows: pyinstaller AttendanceTracker.spec

from PyInstaller.utils.hooks import collect_all
# Analysis, EXE, PYZ are provided as globals by PyInstaller when it runs the spec

# PySide6: collect plugins (e.g. platforms/qwindows.dll) and data
pyside_datas, pyside_binaries, pyside_hidden = collect_all('PySide6')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=pyside_binaries,
    datas=[('app/assets', 'app/assets')] + pyside_datas,
    hiddenimports=pyside_hidden + [
        'pynput.keyboard',
        'pynput.mouse',
        'pynput._util',
        'mss',
        'mss.windows',
        'mss.tools',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AttendanceTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # No black console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
