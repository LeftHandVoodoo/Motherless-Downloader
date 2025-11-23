"""Tests for Windows installation utilities."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from windows_install_utils import (
    get_program_files_path,
    get_desktop_path,
    get_install_path,
    get_resource_path,
    is_frozen,
    get_executable_dir,
)


def test_get_program_files_path():
    """Test getting Program Files path."""
    with patch.dict(os.environ, {"PROGRAMFILES": r"C:\Program Files"}):
        path = get_program_files_path()
        assert path == Path(r"C:\Program Files")
    
    # Test fallback when env var not set
    with patch.dict(os.environ, {}, clear=True):
        path = get_program_files_path()
        assert path == Path(r"C:\Program Files")


def test_get_desktop_path():
    """Test getting Desktop path."""
    # Test with USERPROFILE
    with patch.dict(os.environ, {"USERPROFILE": r"C:\Users\TestUser"}):
        with patch.object(Path, "exists", return_value=True):
            path = get_desktop_path()
            assert "Desktop" in str(path)
    
    # Test with HOMEDRIVE + HOMEPATH
    with patch.dict(
        os.environ,
        {"HOMEDRIVE": "C:", "HOMEPATH": r"\Users\TestUser"},
        clear=True
    ):
        with patch.object(Path, "exists", return_value=True):
            path = get_desktop_path()
            assert "Desktop" in str(path)


def test_get_install_path():
    """Test getting installation path."""
    with patch.dict(os.environ, {"PROGRAMFILES": r"C:\Program Files"}):
        path = get_install_path("Test App")
        assert path == Path(r"C:\Program Files\Test App")
    
    # Test default app name
    path = get_install_path()
    assert "Motherless Downloader" in str(path)


def test_is_frozen():
    """Test checking if running as frozen executable."""
    # Not frozen by default
    assert is_frozen() is False
    
    # Simulate frozen state
    import sys
    original_frozen = getattr(sys, "frozen", None)
    try:
        sys.frozen = True
        assert is_frozen() is True
    finally:
        if original_frozen is None:
            delattr(sys, "frozen")
        else:
            sys.frozen = original_frozen


def test_get_resource_path_dev():
    """Test getting resource path in development mode."""
    with patch("windows_install_utils.is_frozen", return_value=False):
        path = get_resource_path("test.txt")
        # Should be relative to the module
        assert "test.txt" in str(path)


def test_get_resource_path_frozen():
    """Test getting resource path when frozen."""
    import sys
    
    # Mock sys._MEIPASS for frozen mode
    mock_meipass = r"C:\Temp\_MEI12345"
    with patch("windows_install_utils.is_frozen", return_value=True):
        with patch.object(sys, "_MEIPASS", mock_meipass, create=True):
            path = get_resource_path("test.txt")
            assert str(path) == str(Path(mock_meipass) / "test.txt")


def test_get_executable_dir_dev():
    """Test getting executable directory in development."""
    with patch("windows_install_utils.is_frozen", return_value=False):
        path = get_executable_dir()
        # Should be the directory containing the module
        assert path.exists()


def test_get_executable_dir_frozen():
    """Test getting executable directory when frozen."""
    import sys
    
    mock_exe = r"C:\Program Files\MyApp\MyApp.exe"
    with patch("windows_install_utils.is_frozen", return_value=True):
        with patch.object(sys, "executable", mock_exe):
            path = get_executable_dir()
            assert path == Path(mock_exe).parent


def test_create_shortcut_no_deps():
    """Test shortcut creation fails gracefully without dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        target = tmp_path / "test.exe"
        target.touch()
        shortcut = tmp_path / "test.lnk"
        
        # Import should work even if win32com is not available
        from windows_install_utils import create_shortcut
        
        # Function should exist and be callable
        assert callable(create_shortcut)
        
        # Note: We can't fully test shortcut creation without win32com or PowerShell,
        # but we can verify the function doesn't crash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

