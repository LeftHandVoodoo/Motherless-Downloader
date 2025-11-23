"""Windows installation utilities for path resolution and shortcut creation."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def get_program_files_path() -> Path:
    """Get the Program Files directory path."""
    # Try PROGRAMFILES environment variable first
    program_files = os.environ.get("PROGRAMFILES")
    if program_files:
        return Path(program_files)
    
    # Fallback to common location
    return Path(r"C:\Program Files")


def get_desktop_path() -> Path:
    """Get the current user's Desktop path."""
    # Try USERPROFILE first
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        desktop = Path(user_profile) / "Desktop"
        if desktop.exists():
            return desktop
    
    # Try HOMEDRIVE + HOMEPATH
    home_drive = os.environ.get("HOMEDRIVE", "C:")
    home_path = os.environ.get("HOMEPATH", r"\Users\Public")
    desktop = Path(home_drive + home_path) / "Desktop"
    if desktop.exists():
        return desktop
    
    # Last resort fallback
    return Path.home() / "Desktop"


def get_install_path(app_name: str = "Motherless Downloader") -> Path:
    """Get the installation path for the application."""
    return get_program_files_path() / app_name


def create_shortcut(
    target_path: Path,
    shortcut_path: Path,
    icon_path: Optional[Path] = None,
    description: str = "",
    working_directory: Optional[Path] = None,
) -> bool:
    """
    Create a Windows shortcut (.lnk file).
    
    Args:
        target_path: Path to the target executable
        shortcut_path: Path where the shortcut should be created (must end in .lnk)
        icon_path: Optional path to icon file
        description: Optional description for the shortcut
        working_directory: Optional working directory for the shortcut
    
    Returns:
        True if shortcut was created successfully, False otherwise
    """
    try:
        # Import COM libraries for creating shortcuts
        import win32com.client
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = str(target_path)
        
        if icon_path:
            shortcut.IconLocation = str(icon_path)
        
        if description:
            shortcut.Description = description
        
        if working_directory:
            shortcut.WorkingDirectory = str(working_directory)
        else:
            # Default to target's parent directory
            shortcut.WorkingDirectory = str(target_path.parent)
        
        shortcut.Save()
        return True
    except ImportError:
        # win32com not available, try alternative method using powershell
        return _create_shortcut_powershell(
            target_path, shortcut_path, icon_path, description, working_directory
        )
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return False


def _create_shortcut_powershell(
    target_path: Path,
    shortcut_path: Path,
    icon_path: Optional[Path] = None,
    description: str = "",
    working_directory: Optional[Path] = None,
) -> bool:
    """Create shortcut using PowerShell as fallback."""
    import subprocess
    
    if not working_directory:
        working_directory = target_path.parent
    
    # Build PowerShell command
    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{target_path}'
    $Shortcut.WorkingDirectory = '{working_directory}'
    """
    
    if icon_path:
        ps_script += f"\n    $Shortcut.IconLocation = '{icon_path}'"
    
    if description:
        ps_script += f"\n    $Shortcut.Description = '{description}'"
    
    ps_script += "\n    $Shortcut.Save()"
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"PowerShell shortcut creation failed: {e}")
        return False


def get_resource_path(relative_path: str | Path) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller frozen exe.
    
    When frozen by PyInstaller, resources are extracted to sys._MEIPASS.
    In development, resources are relative to the script location.
    
    Args:
        relative_path: Relative path to the resource
    
    Returns:
        Absolute path to the resource
    """
    if getattr(sys, "frozen", False):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent
    
    return base_path / relative_path


def is_frozen() -> bool:
    """Check if running as a frozen PyInstaller executable."""
    return getattr(sys, "frozen", False)


def get_executable_dir() -> Path:
    """Get the directory containing the executable or script."""
    if is_frozen():
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent

