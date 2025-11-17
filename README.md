# Motherless Single Downloader

A PySide6-based GUI application for downloading media files from Motherless with support for multi-connection downloads, pause/resume, and adaptive connection management.

## Features

- **Modern GUI**: Clean, dark-themed interface built with PySide6
- **Multi-Connection Downloads**: Download files using up to 30 parallel connections for faster speeds
- **Adaptive Connection Management**: Automatically adjusts connection count based on server throughput hints
- **Pause/Resume**: Support for pausing and resuming downloads (when server supports range requests)
- **Automatic Filename Detection**: Extracts filenames from server headers or page titles
- **URL Validation**: Validates Motherless URLs before starting downloads
- **Progress Tracking**: Real-time progress bar, speed display (Mb/s), and connection status
- **Resume Support**: Automatically resumes interrupted downloads using sidecar state files
- **Media Discovery**: Automatically discovers direct media URLs from Motherless page URLs

## Requirements

- Python 3.12+ (Python 3.12 recommended for PySide6 compatibility)
- PySide6 6.7.0
- httpx 0.27.0 (with HTTP/2 support)
- beautifulsoup4 4.12.3
- platformdirs 4.2.2

## Installation

1. Clone or download this repository
2. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   ```
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```bash
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
├── main.py                 # GUI entry point (PySide6)
├── downloader/             # Core download engine
│   ├── __init__.py        # Package exports
│   ├── manager.py         # DownloadManager (QThread-based)
│   ├── utils.py           # URL validation, header parsing
│   ├── discover.py        # Media URL and title discovery
│   ├── segments.py        # Download segmentation logic
│   └── state.py           # Sidecar state management
├── tests/                 # Test suite
├── tools/                 # Utility scripts
│   └── probe_motherless.py
├── requirements.txt       # Python dependencies
├── changelog.md          # Change history
└── README.md             # This file
```

## Configuration

The application remembers your last used download directory using QSettings (Windows registry or platform-appropriate storage).

Default download directory: `F:\Debrid Stage` (Windows) or user's home directory if not configured.

## Troubleshooting

- **PySide6 Installation Issues**: If PySide6 fails to install on Python 3.13, use Python 3.12 instead
- **HTTP/2 Support**: The application gracefully falls back to HTTP/1.1 if HTTP/2 is not available
- **Permission Errors**: Sidecar writes are serialized to prevent Windows permission errors
- **Resume Not Working**: Resume only works if the server supports HTTP range requests (Accept-Ranges header)

## Development

See `changelog.md` for detailed change history and development notes.

## License

[Add license information here]

