# Windows Installer - Quick Reference

This document provides quick instructions for building and using the Windows installer for Motherless Downloader.

## For End Users

### Installing the Application

1. Download `MotherlessDownloaderSetup.exe`
2. Double-click to run the installer
3. Grant administrator permissions when prompted (required for Program Files installation)
4. Follow the installation prompts
5. Launch from the desktop shortcut created during installation

The application will:
- Install to `C:\Program Files\Motherless Downloader`
- Create a desktop shortcut with icon
- Automatically start the web server and open your browser when launched

### Uninstalling

To remove the application:
1. Delete the installation directory: `C:\Program Files\Motherless Downloader`
2. Delete the desktop shortcut
3. Optionally delete user data at: `%LOCALAPPDATA%\LeftHandVoodoo\MotherlessDownloader\`

## For Developers

### Prerequisites

- Python 3.12+ with all dependencies installed (`pip install -r requirements.txt`)
- Node.js 18+ for frontend build
- PyInstaller and pywin32: `pip install pyinstaller pywin32`
- Frontend must be built before creating installer

### Building the Installer

#### Quick Build (Recommended)

```bash
# On Windows
build_installer.bat

# Or with Python
python build_installer.py
```

This automated script will:
1. Check if frontend is built (and prompt if not)
2. Build `MotherlessDownloader.exe` (main application)
3. Build `MotherlessDownloaderSetup.exe` (installer)
4. Report final installer location and size

#### Manual Build (Advanced)

```bash
# 1. Build frontend (if not already done)
cd frontend
npm install
npm run build
cd ..

# 2. Build main application
pyinstaller --clean --noconfirm motherless_app.spec

# 3. Build installer
pyinstaller --clean --noconfirm installer.spec
```

### Output Files

After building, you'll find:

- `dist/MotherlessDownloader.exe` - Main application (bundled web interface)
- `dist/MotherlessDownloaderSetup.exe` - Installer that includes the main app

The installer is typically 40-80 MB depending on dependencies.

### Testing the Installer

1. Run `dist/MotherlessDownloaderSetup.exe`
2. Complete the installation
3. Launch from desktop shortcut
4. Verify web interface opens at http://localhost:8000
5. Test downloading a file to ensure functionality

### Project Structure

```
.
├── windows_install_utils.py    # Windows path/shortcut helpers
├── web_launcher.py              # Production web interface launcher
├── installer_win.py             # Installer script
├── build_installer.py           # Automated build script
├── build_installer.bat          # Windows batch wrapper
├── motherless_app.spec          # PyInstaller spec for main app
├── installer.spec               # PyInstaller spec for installer
└── tests/
    └── test_windows_install_utils.py  # Unit tests for utilities
```

### How It Works

1. **Main Application Build** (`motherless_app.spec`):
   - Freezes `web_launcher.py` with PyInstaller
   - Bundles `frontend/dist/**` (React build)
   - Bundles `ml.yaml` (configuration)
   - Bundles `icon/icon.ico` (application icon)
   - Includes all Python dependencies
   - Results in single-file `MotherlessDownloader.exe`

2. **Installer Build** (`installer.spec`):
   - Freezes `installer_win.py` with PyInstaller
   - Bundles the `MotherlessDownloader.exe` as data
   - Bundles `icon.ico` for shortcut creation
   - Results in single-file `MotherlessDownloaderSetup.exe`

3. **Installation Process** (`installer_win.py`):
   - Checks for admin rights (warns if missing)
   - Creates `C:\Program Files\Motherless Downloader\`
   - Copies `MotherlessDownloader.exe` and icon
   - Creates desktop shortcut using Windows COM API
   - Reports success/failure with clear messages

4. **Runtime Behavior** (`web_launcher.py`):
   - Starts uvicorn server without reload mode
   - Opens browser to http://localhost:8000
   - Uses `windows_install_utils.get_resource_path()` to locate bundled assets
   - `api/main.py` detects frozen state and resolves frontend/dist correctly

### Troubleshooting

**Build Issues:**

- "Frontend not built": Run `cd frontend && npm install && npm run build`
- "PyInstaller not found": Run `pip install pyinstaller`
- "win32com not found": Run `pip install pywin32`
- Large build size: This is normal; includes Python runtime and all dependencies

**Installation Issues:**

- Permission denied: Run installer as Administrator (right-click → Run as administrator)
- Desktop shortcut not created: May occur without pywin32; shortcut creation will fall back to PowerShell

**Runtime Issues:**

- Port 8000 already in use: Close any process using that port
- Frontend not loading: Check that frontend/dist was included in build
- "Module not found" errors: Hidden imports may need to be added to spec file

### Development Notes

- Keep `run.py` for development use (includes `--reload`)
- Use `web_launcher.py` for production/frozen builds (no reload)
- `windows_install_utils.py` handles both dev and frozen modes transparently
- Tests use mocks to avoid requiring actual Windows COM APIs
- Version number is intentionally not bumped (remains 0.3.2)

### Future Enhancements

Potential improvements for future versions:

- [ ] Add uninstaller script
- [ ] Support for custom installation directory
- [ ] Start Menu shortcuts in addition to desktop
- [ ] Windows Registry entries for file associations
- [ ] Auto-update mechanism
- [ ] Code signing certificate for installer
- [ ] Silent installation mode (`/S` flag)
- [ ] Multi-language support in installer

## Support

For issues or questions:
- Check the main README.md for general usage
- Review changelog.md for recent changes
- Run tests: `pytest tests/test_windows_install_utils.py`

