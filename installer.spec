# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for building MotherlessDownloaderSetup.exe
This builds the installer that bundles the main application exe.

Build with: pyinstaller installer.spec
"""
from pathlib import Path

# Get absolute paths
project_root = Path(SPECPATH)
dist_dir = project_root / "dist"
main_exe = dist_dir / "MotherlessDownloader.exe"
icon_file = project_root / "icon" / "icon.ico"

# Bundle the main application exe and icon
datas = []
if main_exe.exists():
    datas.append((str(main_exe), "."))
else:
    print("WARNING: MotherlessDownloader.exe not found in dist/")
    print("         Build the main app first: pyinstaller motherless_app.spec")

if icon_file.exists():
    datas.append((str(icon_file), "."))

# Hidden imports
hiddenimports = [
    'win32com.client',
    'win32com.shell',
    'win32com.shell.shell',
    'pywintypes',
]

block_cipher = None


a = Analysis(
    ['installer_win.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
        'PySide6',
        'PyQt5',
        'PyQt6',
        'fastapi',  # Not needed in installer
        'uvicorn',
        'httpx',
        'beautifulsoup4',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MotherlessDownloaderSetup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for installer output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
)

