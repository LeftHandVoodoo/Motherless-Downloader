# Motherless Downloader

A modern download manager for Motherless media files with two interface options:
- **Web Interface** (v0.3.2): FastAPI + React with real-time WebSocket updates, multi-download queue, persistent history, automatic quality selection, video thumbnails, and filename normalization
- **Desktop GUI** (Legacy): PySide6-based traditional desktop application

Both interfaces share the same robust download engine with multi-connection support, pause/resume, adaptive connection management, and automatic highest quality selection.

## Features

### Core Download Engine
- **Multi-Connection Downloads**: Up to 30 parallel connections for maximum speed
- **Adaptive Connection Management**: Auto-adjusts connections based on server throughput
- **Pause/Resume**: Full pause/resume support with persistent state
- **Automatic Filename Detection**: Smart extraction from headers or page titles
- **Highest Quality Selection**: Automatically detects and downloads the highest quality version when multiple sources are available
- **Filename Normalization**: Automatically normalizes filenames by removing random numbers, applying title case, and normalizing spacing
- **URL Validation**: Strict HTTPS and domain validation
- **Media Discovery**: Auto-discovers direct media URLs from page URLs
- **Cross-Platform**: Windows, Linux, macOS support

### Web Interface (v0.3.2)
- **Modern React UI**: Beautiful glassmorphism design with dark theme
- **Download Queue**: Manage multiple downloads simultaneously with configurable concurrency
- **Real-Time Updates**: WebSocket-based live progress tracking with optimized throttling
- **Download History**: Persistent SQLite database tracking all downloads with search, filter, and statistics
- **Video Thumbnails**: Automatic thumbnail extraction from completed video downloads (requires ffmpeg)
- **Open in VLC**: Double-click thumbnails in history to open files in VLC media player
- **Filename Normalization**: Automatically normalizes filenames by removing random numbers, applying title case, and normalizing spacing
- **Redownload from History**: One-click redownload button available for all history items (not just completed)
- **File Existence Tracking**: Automatically tracks whether downloaded files still exist at their save location
- **Enhanced Filename Tracking**: Tracks both URL filename and actual saved filename
- **Statistics Dashboard**: Live overview of total, active, completed, and failed downloads
- **Smart Cleanup**: Auto-cleanup of old downloads with manual "Clear Completed" button
- **URL Validation**: Instant feedback on invalid URLs before download starts
- **REST API**: Full programmatic control via REST endpoints
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Status Indicators**: Visual feedback for queued, downloading, paused, completed states
- **Reliability**: Fixed memory leaks, proper thread cleanup, atomic settings writes, and automatic partial file cleanup

### Desktop GUI (Legacy)
- **PySide6 Interface**: Traditional Qt-based desktop application
- **Single Download**: Focus on one download at a time
- **Simple Controls**: Easy-to-use buttons for pause/resume/cancel

## Requirements

### Backend (Both Interfaces)
- Python 3.12+ recommended
- httpx 0.27.0 (with HTTP/2 support)
- beautifulsoup4 4.12.3
- platformdirs 4.2.2
- FastAPI 0.109.0 (for web interface)
- uvicorn 0.27.0 (for web interface)
- tzdata>=2024.1 (for Eastern Time zone support)
- **ffmpeg** (optional, for video thumbnail extraction): Install from [ffmpeg.org](https://ffmpeg.org/download.html) or via package manager
- **VLC Media Player** (optional, for opening files from history): Install from [videolan.org](https://www.videolan.org/) or via package manager

### Frontend (Web Interface Only)
- Node.js 18+ (for development)
- npm or yarn

### Legacy GUI Only
- PySide6 6.7.0

## Quick Start

### Option 1: Windows Installer (Easiest - Windows 11 Pro)

**For Windows users**, use the pre-built installer for the quickest setup:

1. **Download** `MotherlessDownloaderSetup.exe` from the releases page

2. **Run the installer**:
   - Double-click `MotherlessDownloaderSetup.exe`
   - Grant administrator permissions when prompted (required for Program Files installation)
   - Follow the installation prompts

3. **Launch the application**:
   - Use the desktop shortcut created during installation
   - Or run from: `C:\Program Files\Motherless Downloader\MotherlessDownloader.exe`

4. The application will automatically:
   - Start a local web server on port 8000
   - Open your default browser to the web interface
   - Display a console window showing server logs

**Building the Installer Yourself:**

If you want to build the installer from source:

```bash
# 1. Ensure frontend is built
cd frontend
npm install
npm run build
cd ..

# 2. Install PyInstaller
pip install pyinstaller pywin32

# 3. Build the installer
python build_installer.py
# Or on Windows: build_installer.bat

# 4. The installer will be created at: dist/MotherlessDownloaderSetup.exe
```

The installer includes:
- Complete web interface (frontend + backend)
- All dependencies bundled (no Python installation required on target machine)
- Application icon and desktop shortcut
- Configuration files (`ml.yaml`) pre-configured

### Option 2: Web Interface (From Source)

### Option 2: Web Interface (From Source)

1. **Clone and install Python dependencies:**
   ```bash
   git clone <repository-url>
   cd Motherless-Downloader
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Install and build frontend:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

3. **Start the server:**
   ```bash
   python run.py
   ```

4. **Open browser:** Navigate to `http://localhost:8000`

### Option 3: Development Mode (Frontend + Backend)

### Option 3: Development Mode (Frontend + Backend)

1. **Terminal 1 - Start backend:**
   ```bash
   python run.py
   ```

2. **Terminal 2 - Start frontend dev server:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open browser:** Navigate to `http://localhost:5173`

### Option 4: Legacy Desktop GUI

1. **Install and run:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

2. **Enter URL**: Paste a Motherless direct HTTPS URL or a Motherless page URL in the URL field
   - The application will automatically discover the direct media URL if you provide a page URL
   - **Quality Selection**: If multiple quality options are available, the highest quality version will be automatically selected
   - URLs are validated before download starts

3. **Select Destination**: Click "Browse…" to choose where to save the file, or use the default directory

4. **Optional Filename**: Enter a custom filename (optional). If left empty, the filename will be auto-detected from the server or page title

5. **Configure Connections**: 
   - Set the number of parallel connections (1-30)
   - Toggle "Adapt ON" to enable adaptive connection management (recommended)
   - Adaptive mode automatically adjusts connections based on server throughput

6. **Start Download**: Click "Download" to begin

7. **Control Download**:
   - **Pause**: Temporarily pause the download (only available if server supports range requests)
   - **Resume**: Continue a paused download
   - **Cancel**: Stop the download and clean up

## How It Works

- **URL Validation**: Validates that URLs are HTTPS and from allowed Motherless domains
- **Media Discovery**: If a page URL is provided, the application scrapes the page to find the direct media URL
- **Quality Selection**: When multiple video sources are available, automatically detects and selects the highest quality version based on:
  - Resolution attributes (width × height) when available
  - Quality labels (e.g., "1080p", "720p") parsed from HTML
  - File size comparison via HEAD requests when resolution info is unavailable
- **HEAD Request**: Performs a HEAD request to determine file size, content type, and whether range requests are supported
- **Segmented Download**: Splits the download into segments when range requests are supported, allowing parallel connections
- **State Management**: Creates sidecar `.state` files to track download progress and enable resume functionality
- **Adaptive Connections**: Monitors per-connection throughput and adjusts connection count to optimize total download speed
- **Thumbnail Extraction**: After video downloads complete, automatically extracts a thumbnail frame using ffmpeg (if available)
- **Thumbnail Cache**: Thumbnails are stored in a `.thumbnails` cache directory inside the download directory for better organization
- **VLC Integration**: Double-click thumbnails in history view to open files directly in VLC media player
- **History Tracking**: All downloads are automatically tracked in SQLite database with full metadata including URL filename, actual filename, save location, and file existence status

## Project Structure

```
.
├── api/                   # FastAPI backend (NEW)
│   ├── main.py           # FastAPI app with REST & WebSocket
│   ├── queue_manager.py  # Multi-download queue manager
│   └── models.py         # Pydantic models
├── downloader/           # Core download engine
│   ├── manager.py        # DownloadManager (thread-based)
│   ├── utils.py          # URL validation, header parsing
│   ├── discover.py       # Media URL discovery with quality selection
│   ├── segments.py       # Download segmentation
│   ├── state.py          # Resume state management
│   ├── history.py        # Download history database management
│   └── thumbnail.py      # Video thumbnail extraction (ffmpeg)
├── frontend/             # React web interface (NEW)
│   ├── src/              # React components
│   ├── package.json      # Node.js dependencies
│   └── vite.config.ts    # Vite configuration
├── main.py               # Legacy PySide6 GUI entry point
├── run.py                # Web interface startup script
├── tests/                # Test suite
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## API Documentation

When running the web interface, full API documentation is available at:
- **Interactive API docs (Swagger)**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc

### Key Endpoints

**Downloads**
- `GET /api/downloads` - List all downloads
- `POST /api/downloads` - Add new download (with URL validation)
- `POST /api/downloads/cleanup` - Clean up old completed/failed/cancelled downloads
- `POST /api/downloads/{id}/pause` - Pause download
- `POST /api/downloads/{id}/resume` - Resume download
- `POST /api/downloads/{id}/cancel` - Cancel download
- `DELETE /api/downloads/{id}` - Remove from queue

**History**
- `GET /api/history` - Get download history (with pagination, search, status filter)
- `GET /api/history/statistics` - Get aggregate statistics
- `GET /api/history/{id}` - Get specific history item
- `GET /api/history/{id}/thumbnail` - Get thumbnail image for a history item
- `POST /api/history/{id}/open` - Open file in VLC media player
- `DELETE /api/history/{id}` - Delete from history
- `POST /api/history/{id}/redownload` - Redownload a file from history
- `POST /api/history/clear` - Clear old history entries
- `GET /api/history/db-path` - Get path to history database file

**Settings**
- `GET /api/settings` - Get current settings
- `PATCH /api/settings` - Update settings
- `WS /ws` - WebSocket for real-time updates

## Configuration

Settings are managed via the API and persisted per session:
- Download directory (defaults to user's Downloads folder)
- Default connection count
- Adaptive mode preference

### Download History Database

The download history is stored in a SQLite database at a platform-appropriate location:
- **Windows**: `%LOCALAPPDATA%\LeftHandVoodoo\MotherlessDownloader\history.db` (typically `C:\Users\<username>\AppData\Local\LeftHandVoodoo\MotherlessDownloader\history.db`)
- **Linux**: `~/.local/share/MotherlessDownloader/history.db`
- **macOS**: `~/Library/Application Support/MotherlessDownloader/history.db`

**Database Schema:**
- Tracks URL, filename (actual saved name), URL filename (from URL), destination path
- Records status, file size, download speed, connection count, adaptive mode
- Stores thumbnail path (if extracted), file existence status
- Includes timestamps (created_at, completed_at, updated_at)
- Automatically checks file existence when retrieving history items

The database path is displayed in the History tab of the web interface. You can open the database file with any SQLite viewer (e.g., [DB Browser for SQLite](https://sqlitebrowser.org/), [SQLiteStudio](https://sqlitestudio.pl/), or command-line `sqlite3`) to inspect or export the data directly.

**History Features:**
- **Search & Filter**: Search by filename/URL, filter by status (completed, failed, cancelled)
- **Video Thumbnails**: Visual previews of downloaded videos (requires ffmpeg)
- **Open in VLC**: Double-click thumbnails to open files in VLC media player
- **File Existence Indicators**: Visual indicators show whether files still exist at their save location
- **Redownload**: One-click redownload button for all history items (preserves original settings)
- **Statistics**: Aggregate statistics showing total downloads, completed/failed counts, total bytes downloaded
- **Filename Normalization**: All new downloads automatically have normalized filenames. Use `migrate_normalize_filenames.py` to normalize existing history entries.

## Migration Tools

### Normalize Existing Filenames

If you have existing downloads in your history database with unnormalized filenames, you can use the migration script to normalize them:

```bash
# Preview what would be changed (dry run)
python migrate_normalize_filenames.py --dry-run

# Update database entries only (doesn't rename files)
python migrate_normalize_filenames.py

# Update database AND rename actual files on disk
python migrate_normalize_filenames.py --rename-files
```

The script will:
- Read all downloads from your history database
- Normalize filenames using the same logic as new downloads
- Update database entries with normalized names
- Optionally rename actual files on disk to match

## Troubleshooting

### General
- **Python Version**: Use Python 3.12 for best compatibility
- **HTTP/2 Support**: Gracefully falls back to HTTP/1.1 if unavailable
- **Permission Errors**: Sidecar writes are throttled and locked to prevent conflicts
- **Resume Not Working**: Requires server support for range requests
- **Memory Usage**: v0.2.2 includes fixes for memory leaks and proper resource cleanup
- **Settings Corruption**: Settings are now written atomically to prevent corruption on crashes

### Web Interface
- **Port Already in Use**: Stop any process using port 8000 or change port in `run.py`
- **WebSocket Connection Failed**: Ensure backend is running and accessible
- **CORS Errors**: Check that frontend proxy is configured correctly in `vite.config.ts`
- **Build Errors**: Run `npm install` again, ensure Node.js 18+ is installed
- **Thumbnails Not Showing**: Ensure ffmpeg is installed and accessible in PATH; check server logs for extraction errors. Thumbnails are stored in `.thumbnails` directory inside your download folder.
- **File Existence Shows Missing**: Files may have been moved or deleted; redownload button available to re-download
- **VLC Not Opening Files**: Ensure VLC media player is installed. The application searches common installation paths and PATH. If VLC is installed in a non-standard location, add it to your system PATH.
- **Timezone Issues**: All timestamps are stored in Eastern Time (EST/EDT). Install `tzdata` package (`pip install tzdata`) for proper daylight saving time handling. The application will fall back to manual offset calculation if `tzdata` is unavailable.

### Legacy GUI
- **PySide6 Issues**: If PySide6 fails on Python 3.13, use Python 3.12 instead
- **Qt Platform Plugin Error**: Install required system Qt libraries for your OS

## Development

See `changelog.md` for detailed change history and development notes.

## License

[Add license information here]

