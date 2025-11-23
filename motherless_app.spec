# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for building MotherlessDownloader.exe
This builds the main web interface application.

Build with: pyinstaller motherless_app.spec
"""
from pathlib import Path
import sys

# Get absolute paths
project_root = Path(SPECPATH)
frontend_dist = project_root / "frontend" / "dist"
icon_file = project_root / "icon" / "icon.ico"
ml_yaml = project_root / "ml.yaml"

# Collect all frontend dist files
frontend_data = []
if frontend_dist.exists():
    # Add all files from frontend/dist recursively
    for item in frontend_dist.rglob("*"):
        if item.is_file():
            relative_path = item.relative_to(project_root)
            dest_dir = str(relative_path.parent)
            frontend_data.append((str(item), dest_dir))

# Add configuration files
config_data = []
if ml_yaml.exists():
    config_data.append((str(ml_yaml), "."))

# Combine all data files
datas = frontend_data + config_data

# Hidden imports needed for the application
hiddenimports = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'platformdirs',
    'win32com.client',
    'win32com.shell',
    'win32com.shell.shell',
    'pywintypes',
]

block_cipher = None


a = Analysis(
    ['web_launcher.py'],
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
        'PySide6',  # Exclude desktop GUI deps
        'PyQt5',
        'PyQt6',
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
    name='MotherlessDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Show console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
)

