#!/usr/bin/env python3
"""
Build script for creating MotherlessDownloaderSetup.exe

This script automates the entire build process:
1. Ensures frontend is built
2. Builds MotherlessDownloader.exe (main app)
3. Builds MotherlessDownloaderSetup.exe (installer)
"""
from __future__ import annotations

import subprocess
import sys
import shutil
from pathlib import Path


def run_command(cmd: list[str], cwd: Path | None = None, description: str = "") -> bool:
    """
    Run a command and return success status.
    
    Args:
        cmd: Command and arguments as list
        cwd: Working directory for the command
        description: Description to print before running
    
    Returns:
        True if command succeeded (exit code 0), False otherwise
    """
    if description:
        print(f"\n{'='*70}")
        print(f"  {description}")
        print('='*70)
    
    print(f"Running: {' '.join(cmd)}")
    if cwd:
        print(f"Working directory: {cwd}")
    print()
    
    result = subprocess.run(cmd, cwd=cwd, check=False)
    
    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        return False
    
    print(f"\n✓ {description or 'Command'} completed successfully")
    return True


def check_pyinstaller() -> bool:
    """Check if PyInstaller is available."""
    if shutil.which("pyinstaller"):
        return True
    
    print("❌ PyInstaller not found!")
    print("\nPlease install it:")
    print("  pip install pyinstaller")
    return False


def check_frontend_built(project_root: Path) -> bool:
    """Check if frontend is built."""
    frontend_dist = project_root / "frontend" / "dist"
    index_html = frontend_dist / "index.html"
    
    if not index_html.exists():
        print("⚠️  Frontend not built!")
        print("\nPlease build the frontend first:")
        print("  cd frontend")
        print("  npm install")
        print("  npm run build")
        return False
    
    print("✓ Frontend is built")
    return True


def build_main_app(project_root: Path) -> bool:
    """Build MotherlessDownloader.exe"""
    spec_file = project_root / "motherless_app.spec"
    
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    return run_command(
        ["pyinstaller", "--clean", "--noconfirm", str(spec_file)],
        cwd=project_root,
        description="Building MotherlessDownloader.exe (main application)"
    )


def build_installer(project_root: Path) -> bool:
    """Build MotherlessDownloaderSetup.exe"""
    spec_file = project_root / "installer.spec"
    
    if not spec_file.exists():
        print(f"❌ Spec file not found: {spec_file}")
        return False
    
    # Check that main app was built
    main_exe = project_root / "dist" / "MotherlessDownloader.exe"
    if not main_exe.exists():
        print(f"❌ Main application not found: {main_exe}")
        print("   Build the main app first.")
        return False
    
    return run_command(
        ["pyinstaller", "--clean", "--noconfirm", str(spec_file)],
        cwd=project_root,
        description="Building MotherlessDownloaderSetup.exe (installer)"
    )


def main():
    """Main build routine."""
    project_root = Path(__file__).parent
    
    print("=" * 70)
    print("  Motherless Downloader - Windows Installer Build Script")
    print("=" * 70)
    print()
    
    # Pre-flight checks
    print("Running pre-flight checks...")
    print()
    
    if not check_pyinstaller():
        return 1
    
    if not check_frontend_built(project_root):
        response = input("\nContinue anyway? (not recommended) [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print("\n❌ Build cancelled.")
            return 1
    
    # Build main application
    if not build_main_app(project_root):
        print("\n❌ Failed to build main application!")
        return 1
    
    # Build installer
    if not build_installer(project_root):
        print("\n❌ Failed to build installer!")
        return 1
    
    # Success!
    dist_dir = project_root / "dist"
    setup_exe = dist_dir / "MotherlessDownloaderSetup.exe"
    
    print("\n" + "=" * 70)
    print("  ✅ Build Complete!")
    print("=" * 70)
    print(f"\nInstaller created: {setup_exe}")
    print(f"Size: {setup_exe.stat().st_size / 1_048_576:.1f} MB")
    print("\nYou can now distribute this installer to users.")
    print("\nTo test the installer:")
    print(f"  1. Run: {setup_exe}")
    print("  2. Follow the installation prompts")
    print("  3. Launch from the desktop shortcut")
    print()
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Build cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

