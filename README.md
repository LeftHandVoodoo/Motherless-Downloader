# Motherless Downloader

A modern download manager for Motherless media files with two interface options:
- **Web Interface** (v0.2.2): FastAPI + React with real-time WebSocket updates, multi-download queue
- **Desktop GUI** (Legacy): PySide6-based traditional desktop application

Both interfaces share the same robust download engine with multi-connection support, pause/resume, and adaptive connection management.

## Features

### Core Download Engine
- **Multi-Connection Downloads**: Up to 30 parallel connections for maximum speed
- **Adaptive Connection Management**: Auto-adjusts connections based on server throughput
- **Pause/Resume**: Full pause/resume support with persistent state
- **Automatic Filename Detection**: Smart extraction from headers or page titles
- **URL Validation**: Strict HTTPS and domain validation
- **Media Discovery**: Auto-discovers direct media URLs from page URLs
- **Cross-Platform**: Windows, Linux, macOS support

### Web Interface (v0.2.2)
- **Modern React UI**: Beautiful glassmorphism design with dark theme
- **Download Queue**: Manage multiple downloads simultaneously with configurable concurrency
- **Real-Time Updates**: WebSocket-based live progress tracking with optimized throttling
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

### Frontend (Web Interface Only)
- Node.js 18+ (for development)
- npm or yarn

### Legacy GUI Only
- PySide6 6.7.0

## Quick Start

### Option 1: Web Interface (Recommended)

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

### Option 2: Development Mode (Frontend + Backend)

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

### Option 3: Legacy Desktop GUI

1. **Install and run:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

2. **Enter URL**: Paste a Motherless direct HTTPS URL or a Motherless page URL in the URL field
   - The application will automatically discover the direct media URL if you provide a page URL
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
- **HEAD Request**: Performs a HEAD request to determine file size, content type, and whether range requests are supported
- **Segmented Download**: Splits the download into segments when range requests are supported, allowing parallel connections
- **State Management**: Creates sidecar `.state` files to track download progress and enable resume functionality
- **Adaptive Connections**: Monitors per-connection throughput and adjusts connection count to optimize total download speed

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
│   ├── discover.py       # Media URL discovery
│   ├── segments.py       # Download segmentation
│   └── state.py          # Resume state management
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
- `GET /api/downloads` - List all downloads
- `POST /api/downloads` - Add new download (with URL validation)
- `POST /api/downloads/cleanup` - Clean up old completed/failed/cancelled downloads
- `POST /api/downloads/{id}/pause` - Pause download
- `POST /api/downloads/{id}/resume` - Resume download
- `POST /api/downloads/{id}/cancel` - Cancel download
- `DELETE /api/downloads/{id}` - Remove from queue
- `GET /api/settings` - Get current settings
- `PATCH /api/settings` - Update settings
- `WS /ws` - WebSocket for real-time updates

## Configuration

Settings are managed via the API and persisted per session:
- Download directory (defaults to user's Downloads folder)
- Default connection count
- Adaptive mode preference

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

### Legacy GUI
- **PySide6 Issues**: If PySide6 fails on Python 3.13, use Python 3.12 instead
- **Qt Platform Plugin Error**: Install required system Qt libraries for your OS

## Development

See `changelog.md` for detailed change history and development notes.

## License

[Add license information here]

