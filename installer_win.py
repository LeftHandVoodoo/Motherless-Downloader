#!/usr/bin/env python3
"""
Windows installer for Motherless Downloader.

This script installs the application to Program Files and creates a desktop shortcut.
When built with PyInstaller, this becomes MotherlessDownloaderSetup.exe.
"""
from __future__ import annotations

import sys
import shutil
import traceback
from pathlib import Path

from windows_install_utils import (
    get_install_path,
    get_desktop_path,
    create_shortcut,
    get_resource_path,
    is_frozen,
)


APP_NAME = "Motherless Downloader"
EXE_NAME = "MotherlessDownloader.exe"
SHORTCUT_NAME = "Motherless Downloader.lnk"


def print_header():
    """Print installer header."""
    print("=" * 70)
    print(f"  {APP_NAME} - Windows Installer")
    print("=" * 70)
    print()


def check_admin_rights() -> bool:
    """Check if running with administrator privileges."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def install_application(install_dir: Path, source_exe: Path, icon_source: Path) -> bool:
    """
    Install the application to the target directory.
    
    Args:
        install_dir: Target installation directory
        source_exe: Path to MotherlessDownloader.exe in the installer bundle
        icon_source: Path to icon.ico in the installer bundle
    
    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        print(f"📁 Creating installation directory: {install_dir}")
        install_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy main executable
        target_exe = install_dir / EXE_NAME
        print(f"📦 Copying {EXE_NAME}...")
        shutil.copy2(source_exe, target_exe)
        print(f"   ✓ Installed: {target_exe}")
        
        # Copy icon file
        if icon_source.exists():
            target_icon = install_dir / "icon.ico"
            print(f"🎨 Copying icon...")
            shutil.copy2(icon_source, target_icon)
            print(f"   ✓ Installed: {target_icon}")
        
        return True
    except PermissionError as e:
        print(f"\n❌ Permission denied: {e}")
        print("   Please run the installer as Administrator.")
        return False
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        traceback.print_exc()
        return False


def create_desktop_shortcut(install_dir: Path) -> bool:
    """
    Create a desktop shortcut for the application.
    
    Args:
        install_dir: Installation directory containing the exe
    
    Returns:
        True if shortcut was created successfully, False otherwise
    """
    try:
        desktop = get_desktop_path()
        shortcut_path = desktop / SHORTCUT_NAME
        target_exe = install_dir / EXE_NAME
        icon_path = install_dir / "icon.ico"
        
        print(f"\n🔗 Creating desktop shortcut: {shortcut_path}")
        
        success = create_shortcut(
            target_path=target_exe,
            shortcut_path=shortcut_path,
            icon_path=icon_path if icon_path.exists() else None,
            description=APP_NAME,
            working_directory=install_dir,
        )
        
        if success:
            print(f"   ✓ Shortcut created: {shortcut_path}")
            return True
        else:
            print(f"   ⚠️  Could not create desktop shortcut")
            return False
    except Exception as e:
        print(f"\n⚠️  Failed to create desktop shortcut: {e}")
        return False


def main():
    """Main installer routine."""
    print_header()
    
    # Check for admin rights
    if not check_admin_rights():
        print("⚠️  WARNING: Not running as Administrator")
        print("   Installation to Program Files may fail without admin rights.\n")
    
    # Determine paths
    install_dir = get_install_path(APP_NAME)
    
    # Find bundled executable and icon
    if is_frozen():
        # Running as frozen installer
        # The MotherlessDownloader.exe should be bundled in the installer
        source_exe = get_resource_path(EXE_NAME)
        icon_source = get_resource_path("icon.ico")
    else:
        # Running in development - look for built exe
        project_root = Path(__file__).parent
        dist_dir = project_root / "dist"
        source_exe = dist_dir / EXE_NAME
        icon_source = project_root / "icon" / "icon.ico"
    
    # Validate source files
    if not source_exe.exists():
        print(f"❌ ERROR: Cannot find {EXE_NAME}")
        print(f"   Expected at: {source_exe}")
        print("\n   Please build the application first:")
        print("   python build_installer.py")
        return 1
    
    if not icon_source.exists():
        print(f"⚠️  WARNING: Icon file not found at {icon_source}")
        print("   Continuing without icon...\n")
    
    # Show installation plan
    print(f"Installation directory: {install_dir}")
    print(f"Source executable:      {source_exe}")
    print(f"Icon source:            {icon_source}")
    print()
    
    # Confirm installation
    try:
        response = input("Proceed with installation? [Y/n]: ").strip().lower()
        if response and response not in ("y", "yes"):
            print("\n❌ Installation cancelled by user.")
            return 0
    except (EOFError, KeyboardInterrupt):
        print("\n\n❌ Installation cancelled.")
        return 0
    
    print()
    
    # Perform installation
    if not install_application(install_dir, source_exe, icon_source):
        print("\n❌ Installation failed!")
        return 1
    
    # Create desktop shortcut
    create_desktop_shortcut(install_dir)
    
    # Success
    print("\n" + "=" * 70)
    print(f"✅ Installation complete!")
    print("=" * 70)
    print(f"\nInstalled to: {install_dir}")
    print(f"\nYou can now launch {APP_NAME} from:")
    print(f"  • Desktop shortcut: {get_desktop_path() / SHORTCUT_NAME}")
    print(f"  • Executable: {install_dir / EXE_NAME}")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\n\n❌ Installation cancelled by user.")
        exit_code = 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        exit_code = 1
    
    # Pause before exit so user can see the output
    try:
        input("\nPress Enter to exit...")
    except (EOFError, KeyboardInterrupt):
        pass
    
    sys.exit(exit_code)

