- ✅ **CHANGELOG INITIALIZED**: Created changelog and adopted per-change logging policy
- ✅ **DEVELOPMENT GUIDELINES ADDED**: Created ProjectDevelopmentGuideline.md with coding standards, workflow, and modern UI guidance
- ✅ **CURRENT PHASE ESTABLISHED**: Added CurrentPhase.md with phased roadmap and active Phase 0 log
- ✅ **DOWNLOADER PACKAGE ADDED**: Created downloader/__init__.py to expose validation utilities
- ✅ **VALIDATION UTILITIES IMPLEMENTED**: Added downloader/utils.py for URL and HEAD validation with type hints
- ✅ **TESTS ADDED**: Created tests/tests_validate.py covering URL validation, filename extraction, and HEAD checks
- ✅ **REQUIREMENTS BASELINE**: Added pinned requirements.txt (PySide6, httpx, platformdirs)
- ✅ **PHASE 1 PROGRESS LOGGED**: Updated CurrentPhase.md to Active Phase 1 with completed tasks and next scope
- ✅ **SIDECAR HELPERS ADDED**: Created downloader/state.py for atomic sidecar save/load and resume helpers
- ✅ **DOWNLOAD MANAGER IMPLEMENTED**: Added downloader/manager.py (QThread httpx streaming with pause/resume/cancel, sidecar)
- ✅ **STATE TESTS ADDED**: Created tests/test_state.py for sidecar helpers and resume offset
- ✅ **PHASE 2 PROGRESS LOGGED**: Updated CurrentPhase.md to Active Phase 2 with completed deliverables
- ✅ **HEAD INFO SIGNAL**: Enhanced DownloadManager to emit head_info with size, ranges, type, filename
- ✅ **SLEEK GUI CREATED**: Added main.py with modern QSS, controls, progress, and wiring to DownloadManager
- ✅ **IMPORTS DECOUPLED**: Avoided importing manager in downloader/__init__.py to keep tests lightweight
- ✅ **PHASE 3 PROGRESS LOGGED**: Updated CurrentPhase.md to Active Phase 3 with GUI deliverables
- ✅ **ENTRYPOINT AND ENVIRONMENT GUIDANCE**: Confirmed main.py as the entry point; provided run steps and PySide6 installation guidance (use Python 3.12 if PySide6 wheel unavailable on 3.13)
- ✅ **PYRIGHT CONFIG ADDED**: Created pyrightconfig.json to point to .venv and resolve IDE imports
- ✅ **PYRIGHT UPDATED TO 3.12**: Pointed pyright to Python 3.12 venv for PySide6
- ✅ **URL VALIDATION FIX**: Allow base domain motherless.com in validation; added test
- ✅ **HEADER VALIDATION ENHANCED**: Added Content-Range fallback and expanded host allowlist
- ✅ **MEDIA DISCOVERY ADDED**: Implemented discover_media_url with bs4; manager now discovers and sets Referer
- ✅ **PROBE TOOL ADDED**: tools/probe_motherless.py to print HEAD/headers and discovered media
- ✅ **TESTS EXTENDED**: Added tests for Content-Range fallback and host variants
- ✅ **URL JOIN FIX**: Replaced httpx.URL base join with urllib.parse.urljoin and preserved page Referer
- ✅ **INTEGRATION PROBE TEST**: Added test for discovery and URL joining behavior
- ✅ **MULTI-CONNECTION DOWNLOAD**: Implemented segmented downloading with up to 30 connections and GUI control
- ✅ **SPEED CALCULATION IMPROVED**: Emit rate based on sliding 3s window during writes
- ✅ **416 FIXES**: Adjusted segments for resume, preflight ranges, preallocated .part, and locked progress updates
- ✅ **GUI STYLING + TELEMETRY**: Log box set to black/green; show active connections; speed now in Mb/s
- ✅ **TITLE DISCOVERY & SUBFOLDER**: Extract page title, sanitize, and save into title-named folder; default download dir set to F:\Debrid Stage
- ✅ **DEBUG LOGGING (CONNECTIONS)**: Added print diagnostics for connection count, per-segment range, bytes downloaded, and retry/backoff
- ✅ **THROTTLING DIAGNOSTICS**: Print Accept-Ranges, Content-Length/Range, Retry-After, server header; per-segment avg speed logs
- ✅ **DEBUG FIX**: Moved _dbg definition before first use to prevent runtime error
- ✅ **THROTTLE ADAPTATION**: Detect rate= query hint and auto-downshift connections to match server per-connection limits, targeting ~4 MB/s total
- ✅ **USER CONTROL FOR ADAPTATION**: Added optional "Adapt" toggle; by default, we do not reduce user-selected connections
- ✅ **TITLE FOLDER CREATION FIX**: Ensure subfolder is created and dependent paths recomputed before writing/renaming

- ✅ **VIDEO EXTENSION INFERENCE**: Use suggested filename and Content-Type to select appropriate video extension when no explicit name is provided; avoids saving as .bin and improves final file naming.

- ✅ **NO SUBFOLDER SAVES**: Stop creating title-named subfolders; instead use discovered page title as the filename (sanitized) with correct extension when no explicit filename is provided.

- ✅ **PROGRESS IN MB**: Changed progress label from bytes to MB (received/total) for readability.

- ✅ **REMEMBER LAST DIRECTORY**: Persist last chosen download directory with QSettings and restore on startup.

- ✅ **SPEED TUNING**: Enable HTTP/2 and allow Adapt mode to increase/decrease connections based on per-connection throughput hints.

- ✅ **ADAPT TOGGLE UI**: Show clear ON/OFF text, green highlight when ON, and append "(Adapt)" to connections label.

- ✅ **HTTP/2 FALLBACK + DEP**: Gracefully fall back to HTTP/1.1 if `h2` is missing; updated `requirements.txt` to `httpx[http2]`.

- ✅ **SIDECAR WRITE LOCK**: Prevent Windows PermissionError by serializing sidecar writes and skipping on contention.

- ✅ **FILENAME OVERRIDE LOGIC**: Clear auto filename on URL change and treat filename as explicit only when user edits it; fixes repeated name without extension across downloads.

- ✅ **ADAPT DEFAULT ON**: Set Adapt to be enabled by default on startup.
- ✅ **DOCUMENTATION ADDED**: Created README.md with installation, usage, and feature documentation; added VERSION file with semantic versioning (0.1.0).

## Version 0.1.1 - Bug Fixes and Improvements

- ✅ **CRITICAL: CANCEL THREAD SAFETY**: Fixed cancel event handling to properly stop all download threads; added download_failed event for coordinated thread shutdown; threads now check cancel/failed status in download loop.
- ✅ **CRITICAL: SPEED WINDOW THREAD SAFETY**: Added window_lock to protect shared speed tracking window list from race conditions during concurrent thread access.
- ✅ **CRITICAL: RESUME URL VALIDATION**: Implemented proper URL validation on resume using sidecar_matches_url; prevents downloading wrong file when URL changes between sessions; clears stale .part files when URL mismatch detected.
- ✅ **CRITICAL: SIDECAR I/O THROTTLING**: Reduced sidecar write frequency from every chunk (~100s/sec) to every 2 seconds, dramatically reducing I/O overhead and PermissionError contention on Windows.
- ✅ **CRITICAL: FINAL STATE PERSISTENCE**: Added final sidecar save before completion to ensure progress is always persisted on error/cancel.
- ✅ **CODE QUALITY: DUPLICATE IMPORT REMOVED**: Removed duplicate `import re as _re` in utils.py; consolidated to single `import re`.
- ✅ **CODE QUALITY: REGEX CLARITY**: Fixed regex capturing groups in filename extraction - replaced numeric group(3) with named groups 'utf8' and 'regular' for better maintainability.
- ✅ **SECURITY: FILE PERMISSIONS VALIDATION**: Added comprehensive permission checks before download starts; validates directory creation and file write access with clear error messages.
- ✅ **TYPE SAFETY: BEAUTIFULSOUP VALIDATION**: Added isinstance() checks in discover.py to handle cases where BeautifulSoup.get() returns list instead of string.
- ✅ **CROSS-PLATFORM: REMOVED HARDCODED PATH**: Replaced Windows-specific "F:/Debrid Stage" with platformdirs.user_downloads_dir() for proper cross-platform defaults.
- ✅ **PERFORMANCE: HTTP/2 CHECK OPTIMIZATION**: Moved HTTP/2 availability check from per-download runtime to module-level constant HTTP2_AVAILABLE; eliminates redundant imports.
- ✅ **UX: IMPROVED ERROR MESSAGES**: Enhanced error messages throughout with specific context (e.g., "Cancelled by user", "Download incomplete: X/Y bytes received. Resume data saved.", "Permission denied: Cannot write to {path}").
- ✅ **RELIABILITY: BETTER EXCEPTION HANDLING**: Added try-except blocks around filesystem operations with specific PermissionError vs general Exception handling.
- ✅ **TESTS: ALL PASSING**: Verified all 13 unit tests pass after changes (URL validation, header parsing, segments, state management, discovery).

## Version 0.2.0 - Major UI Revamp: Modern Web Interface

### 🎨 New Web Interface (FastAPI + React + TypeScript)
- ✅ **FASTAPI BACKEND**: Complete REST API with FastAPI, providing endpoints for download management, settings, and queue operations.
- ✅ **WEBSOCKET REAL-TIME UPDATES**: WebSocket integration for live progress updates; eliminates polling, provides instant status changes.
- ✅ **MULTI-DOWNLOAD QUEUE**: QueueManager system supporting concurrent downloads with configurable max concurrency (default: 3 simultaneous downloads).
- ✅ **REACT + TYPESCRIPT FRONTEND**: Modern React 18 application with TypeScript for type safety and better developer experience.
- ✅ **SHADCN/UI COMPONENTS**: Beautiful, accessible components from shadcn/ui with Radix UI primitives.
- ✅ **TAILWIND CSS STYLING**: Utility-first CSS framework for rapid UI development with custom color scheme and dark mode support.
- ✅ **GLASSMORPHISM DESIGN**: Modern aesthetic with backdrop blur effects, gradient backgrounds, and smooth animations.
- ✅ **RESPONSIVE LAYOUT**: Mobile-first design that works seamlessly on desktop, tablet, and mobile devices.
- ✅ **STATUS INDICATORS**: Visual feedback with color-coded status badges (queued=yellow, downloading=blue, paused=orange, completed=green, failed=red, cancelled=gray).
- ✅ **PROGRESS VISUALIZATION**: Real-time progress bars with percentage, speed (KB/s, MB/s), ETA calculation, and bytes transferred display.
- ✅ **DOWNLOAD ACTIONS**: Pause, resume, cancel, and remove actions with intuitive icon buttons per download.
- ✅ **QUEUE MANAGEMENT**: Add multiple downloads simultaneously; automatic queue processing up to concurrency limit.

### 🏗️ Architecture Improvements
- ✅ **API/MODELS SEPARATION**: Clean Pydantic models for request/response validation (DownloadRequest, DownloadInfo, Settings, etc.).
- ✅ **DOWNLOAD TASK ABSTRACTION**: DownloadTask class wrapping DownloadManager with queue-friendly interface.
- ✅ **ASYNC QUEUE PROCESSING**: Asynchronous queue manager with proper locking and concurrent task management.
- ✅ **PROGRESS CALLBACKS**: Callback system for broadcasting updates to all connected WebSocket clients.
- ✅ **REST API ENDPOINTS**: Full CRUD operations on downloads plus pause/resume/cancel/remove actions.
- ✅ **CORS MIDDLEWARE**: Configured for development with Vite dev server support.
- ✅ **API DOCUMENTATION**: Auto-generated Swagger UI and ReDoc documentation at /docs and /redoc.

### 🛠️ Frontend Stack
- ✅ **VITE BUILD TOOL**: Lightning-fast HMR and optimized production builds.
- ✅ **TYPESCRIPT**: Full type safety across components, API client, and utilities.
- ✅ **AXIOS HTTP CLIENT**: Type-safe API communication with axios.
- ✅ **LUCIDE REACT ICONS**: Beautiful, consistent icon set (Download, Pause, Play, X, Trash2, Settings).
- ✅ **FORMATTING UTILITIES**: Helper functions for bytes, speed, duration, and ETA formatting.
- ✅ **CN UTILITY**: clsx + tailwind-merge for conditional className composition.

### 📦 Build & Deployment
- ✅ **PRODUCTION BUILD**: Optimized Vite build with code splitting and minification.
- ✅ **STATIC SERVING**: FastAPI configured to serve built frontend from /frontend/dist.
- ✅ **STARTUP SCRIPT**: Simple run.py script to launch backend server with uvicorn.
- ✅ **DEVELOPMENT MODE**: Dual-server setup (backend on :8000, frontend dev on :5173) with proxy configuration.

### 📚 Documentation
- ✅ **UPDATED README**: Comprehensive guide covering both web and legacy interfaces with quick start instructions.
- ✅ **API DOCUMENTATION**: Detailed endpoint descriptions and WebSocket protocol documentation.
- ✅ **PROJECT STRUCTURE**: Clear explanation of new api/ and frontend/ directories.
- ✅ **TROUBLESHOOTING**: Expanded troubleshooting section for web-specific issues.

### 🔄 Backend Changes
- ✅ **REQUIREMENTS UPDATED**: Added FastAPI, uvicorn, pydantic, websockets to requirements.txt.
- ✅ **LEGACY GUI PRESERVED**: Original PySide6 interface (main.py) remains functional for users who prefer desktop app.
- ✅ **SHARED DOWNLOAD ENGINE**: Both interfaces use the same robust downloader/ package ensuring consistent behavior.

### 🎯 Future-Ready
- ✅ **ELECTRON PACKAGING READY**: Structure prepared for Electron/Tauri desktop app packaging.
- ✅ **EXTENSIBLE API**: Easy to add new endpoints, features, or integrations.
- ✅ **MODERN STACK**: Using latest stable versions of all frameworks and libraries.

## Version 0.2.1 - Critical Bug Fixes & UI Improvements

- ✅ **CRITICAL: STREAM CONTEXT FIX**: Fixed indentation bug where `with client.stream(...)` context was closing before reading response data, causing all download segments to fail with `httpx.StreamClosed` errors. All response stream operations now properly occur within the stream context.
- ✅ **CRITICAL: WEBSOCKET UPDATES FIX**: Fixed Qt signal to asyncio event loop bridge; replaced `asyncio.create_task()` (which doesn't work from Qt threads) with `asyncio.run_coroutine_threadsafe()` for proper thread-safe scheduling. Used `Qt.DirectConnection` for signal connections to ensure callbacks fire immediately from worker threads. Progress, speed, and completion updates now properly broadcast to WebSocket clients.
- ✅ **PROGRESS THROTTLING**: Added throttling to progress emissions (~10 times/second per segment) to prevent overwhelming the WebSocket with hundreds of updates per second; ensures smooth progress bar updates.
- ✅ **SETTINGS UI IMPLEMENTED**: Added functional settings panel to web interface; gear icon now toggles settings view with download directory and default connections configuration.
- ✅ **UI REDESIGN**: Changed color scheme from purple/blue to grayish black (zinc-950/gray-900) with zinc-800/zinc-700 UI elements for better contrast and modern appearance.
- ✅ **BANNER IMAGE**: Replaced text header with banner image from banner/banner_image.png; logo now displays in header.
- ✅ **SETTINGS PERSISTENCE**: Settings now persist to JSON file in user config directory; download directory and connection settings are saved and restored on restart.
- ✅ **BROWSE BUTTON**: Added "Browse" button in settings to select download directory; uses File System Access API (Chrome/Edge) with fallback prompt; validates directory paths via backend endpoint.
- ✅ **RESTART SCRIPT ADDED**: Created restart_server.py utility to stop existing server and start fresh instance.

## Version 0.2.2 - Critical Bug Fixes & Performance Improvements

### 🐛 Critical Bug Fixes
- ✅ **CRITICAL: WEBSOCKET CALLBACK MEMORY LEAK**: Fixed memory leak where WebSocket connections registered progress callbacks but never unregistered on disconnect. Implemented callback ID system with `register_progress_callback()` returning ID and `unregister_progress_callback(callback_id)` for proper cleanup. Callbacks are now properly cleaned up when WebSocket disconnects.
- ✅ **CRITICAL: PROGRESS UPDATE FLOODING**: Added throttling to prevent WebSocket flooding with 100+ progress updates per second. Implemented 0.5-second throttle interval using timestamp tracking; progress updates now fire at most 2x/second, preventing client-side performance degradation.
- ✅ **CRITICAL: RACE CONDITION IN QUEUE PROCESSING**: Fixed race condition where concurrent calls to `_process_queue()` could start more downloads than `max_concurrent` limit. Now marks tasks as DOWNLOADING and adds to active_downloads set BEFORE releasing lock, ensuring proper concurrency control.
- ✅ **CRITICAL: QTHREAD CLEANUP MEMORY LEAK**: Fixed memory leak where QThread instances were never properly cleaned up after downloads completed or failed. Added `wait(3000)` calls to ensure threads finish before cleanup, and set `task.manager = None` to release references. Threads are now properly cleaned up in both success and failure paths.
- ✅ **CRITICAL: PART FILE CLEANUP ON CANCEL/FAILURE**: Fixed disk space leak where `.part` and `.part.json` files were left behind when downloads were cancelled or failed. Now automatically removes partial files on cancel and failure, preventing disk space accumulation over time.
- ✅ **CRITICAL: SETTINGS FILE CORRUPTION RISK**: Fixed potential data corruption where settings file writes could be interrupted by crashes, leaving corrupted JSON. Implemented atomic write pattern using temporary file + `os.replace()` with `fsync()` to ensure all-or-nothing writes. Settings are now safe from corruption on crashes.
- ✅ **WEBSOCKET MESSAGE HANDLING**: Implemented proper WebSocket message handling with JSON parsing, ping/pong support, and `get_status` command. Added error handling for malformed messages and proper logging. WebSocket now supports bidirectional communication beyond just progress updates.
- ✅ **PERIODIC CLEANUP RESILIENCE**: Enhanced periodic cleanup task with retry logic and error recovery. Cleanup task now retries up to 3 times on failure, logs warnings appropriately, and continues running even if individual cleanup cycles fail. Prevents silent failures that could leave old downloads accumulating.
- ✅ **THREAD SAFETY IN CLEANUP**: Fixed race condition where cleanup could remove active downloads. Added checks to ensure tasks are not in `active_downloads` set before removal, with double-checking pattern. Cleanup now safely handles concurrent download operations without data races.
- ✅ **DEBUG PRINT REMOVAL**: Removed debug `print()` statements from `downloader/manager.py` that were cluttering logs. All logging now uses proper logging module for consistent log management.
- ✅ **CRITICAL: WEBSOCKET DISCONNECT ERROR HANDLING**: Fixed error spam when WebSocket clients disconnect. Starlette raises `RuntimeError` instead of `WebSocketDisconnect` in some cases. Added proper handling for both exception types with graceful disconnect detection, preventing log flooding with "Cannot call 'receive' once a disconnect message has been received" errors.
- ✅ **CRITICAL: QTHREAD CLEANUP DEADLOCK FIX**: Fixed "QThread::wait: Thread tried to wait on itself" and "QThread: Destroyed while thread is still running" warnings. Moved thread cleanup from within the thread's own callback to an asynchronous cleanup function running in the asyncio event loop. Uses `asyncio.to_thread()` to run blocking `wait()` calls without blocking the event loop. Threads now properly finish before being destroyed.

### 🔧 Error Handling & Logging
- ✅ **ERROR HANDLING IMPROVED**: Wrapped `_start_download()` in comprehensive try-except block to catch and handle download start failures gracefully; prevents uncaught exceptions from crashing queue manager.
- ✅ **LOGGING MODULE INTEGRATION**: Replaced all debug `print()` statements with proper Python logging module (`logger.debug()`, `logger.info()`, `logger.error()`); enables proper log level filtering and structured logging.

### ✨ New Features
- ✅ **URL VALIDATION**: Added URL validation to `POST /api/downloads` endpoint using `is_valid_url()`; rejects invalid URLs with 400 error before adding to queue, providing immediate feedback.
- ✅ **AUTO-CLEANUP SYSTEM**: Implemented automatic cleanup of old completed/failed/cancelled downloads with configurable `auto_cleanup_hours` (default: 24h) and `max_completed` (default: 100) limits. Periodic cleanup task runs hourly to prevent unbounded memory growth.
- ✅ **MANUAL CLEANUP ENDPOINT**: Added `POST /api/downloads/cleanup` endpoint to manually trigger cleanup of old downloads; returns count of removed downloads.
- ✅ **CLEAR COMPLETED BUTTON**: Added "Clear Completed" button to UI that appears when completed/failed/cancelled downloads exist; triggers manual cleanup via new API endpoint.
- ✅ **DOWNLOAD STATISTICS PANEL**: Added 4-card statistics dashboard showing Total Downloads, Active (downloading), Completed, and Failed counts with color-coded display (blue, green, red).

### 🎨 UI Improvements
- ✅ **RESPONSIVE STATISTICS GRID**: Statistics cards use responsive grid layout (2 columns on mobile, 4 on desktop) with consistent styling.
- ✅ **CONDITIONAL UI ELEMENTS**: Statistics panel and Clear Completed button only appear when relevant (downloads exist, completed items present).

### 🏗️ Architecture Improvements
- ✅ **CALLBACK DICTIONARY SYSTEM**: Changed callback storage from simple list to `Dict[int, Callable]` with auto-incrementing IDs for proper lifecycle management.
- ✅ **PROGRESS NOTIFICATION FORCE FLAG**: Added `force` parameter to `_notify_progress()` to bypass throttling for important status changes (start, complete, error).
- ✅ **TASK STATUS PRE-MARKING**: Queue processing now marks task status before starting async task, preventing race conditions in concurrent scenarios.

### 📊 Performance
- ✅ **REDUCED WEBSOCKET TRAFFIC**: Throttling reduces WebSocket messages from ~100/sec to 2/sec per download, dramatically improving client performance and reducing network overhead.
- ✅ **BOUNDED MEMORY USAGE**: Auto-cleanup prevents unlimited growth of completed downloads list in memory.

### 🔍 Code Quality
- ✅ **CONSISTENT LOGGING**: All debug output now uses logging module with appropriate levels (debug, info, warning, error) instead of print statements.
- ✅ **PROPER RESOURCE CLEANUP**: WebSocket connections now properly clean up associated callbacks, preventing resource leaks.
- ✅ **IMPROVED DOCUMENTATION**: Added detailed docstrings explaining race condition fixes and callback lifecycle management.

## Version 0.3.2 - Filename Normalization

### 📝 Filename Normalization
- ✅ **AUTOMATIC FILENAME NORMALIZATION**: Added `normalize_filename()` function to clean and normalize filenames before saving.
- ✅ **REMOVE TRAILING IDs**: Automatically removes trailing underscore + number/alphanumeric patterns (e.g., "_5377767", "_xhaSMU3", "_13182028").
- ✅ **REMOVE EMBEDDED NUMBERS**: Removes random number strings embedded in filenames (e.g., "video123" -> "Video", "abc123def456" -> "Abcdef").
- ✅ **PRESERVE QUALITY INDICATORS**: Preserves video quality indicators (720p, 1080p, 4K, 8K, HD, SD) with proper formatting.
- ✅ **PRESERVE PARENTHESES**: Preserves parentheses content, especially years (e.g., "(1985)", "(2020)").
- ✅ **PRESERVE MEANINGFUL NUMBERS**: Preserves single and double-digit numbers that are part of meaningful text (e.g., "2 British", "18 year old", "Part 2").
- ✅ **TITLE CASE CAPITALIZATION**: Applies proper title case capitalization (first letter of each word capitalized, common words lowercase, "And" capitalized when connecting phrases).
- ✅ **SPACING NORMALIZATION**: Normalizes spacing by converting underscores, hyphens, and multiple spaces to single spaces.
- ✅ **PRESERVE EXTENSIONS**: File extensions are preserved during normalization.
- ✅ **AUTOMATIC RENAMING**: Files are automatically renamed after download completion if normalization changes the filename.
- ✅ **INTEGRATION**: Normalization applied in both `DownloadManager` (legacy GUI) and `QueueManager` (web interface).

### 🧪 Testing
- ✅ **EDGE CASE HANDLING**: Comprehensive handling of edge cases including trailing IDs, quality indicators, parentheses, meaningful numbers, and various capitalization scenarios.

### 🔧 Migration Tool
- ✅ **FILENAME MIGRATION SCRIPT**: Added `migrate_normalize_filenames.py` script to normalize existing filenames in the history database.
- ✅ **DRY RUN MODE**: Script supports `--dry-run` flag to preview changes without modifying the database.
- ✅ **FILE RENAMING OPTION**: Optional `--rename-files` flag to also rename actual files on disk to match normalized names.
- ✅ **SAFE OPERATION**: Script safely updates database entries and handles errors gracefully, with detailed progress reporting.

### 🎬 VLC Integration
- ✅ **OPEN IN VLC**: Double-click on thumbnails in history view to open files in VLC media player.
- ✅ **CROSS-PLATFORM VLC DETECTION**: Automatically finds VLC installation on Windows, macOS, and Linux.
- ✅ **VISUAL FEEDBACK**: Thumbnails show cursor pointer and hover effect to indicate they're clickable.
- ✅ **ERROR HANDLING**: Clear error messages if VLC is not found or file cannot be opened.

### 🕐 Timezone Support
- ✅ **EASTERN TIME ZONE**: All database timestamps now use Eastern Time (EST/EDT) instead of UTC.
- ✅ **AUTOMATIC DST HANDLING**: Uses `zoneinfo` with `tzdata` package for proper daylight saving time transitions.
- ✅ **FALLBACK SUPPORT**: Falls back to manual EST/EDT offset calculation if `tzdata` is not installed (with simple DST approximation).
- ✅ **REQUIREMENTS UPDATE**: Added `tzdata>=2024.1` to requirements.txt for proper timezone support.

### 🖼️ Thumbnail Cache Directory
- ✅ **SEPARATE CACHE**: Thumbnails are now stored in a `.thumbnails` cache directory inside the download directory.
- ✅ **ORGANIZED STORAGE**: Keeps thumbnails separate from video files for better organization.
- ✅ **UNIQUE NAMING**: Thumbnails use hash-based naming (`{filename}_{hash}.jpg`) to avoid conflicts.
- ✅ **AUTOMATIC CREATION**: Cache directory is created automatically if it doesn't exist.
- ✅ **BACKWARD COMPATIBLE**: Falls back to legacy behavior (same directory as video) if download directory is not provided.

## Version 0.3.1 - Automatic Highest Quality Selection

### 🎯 Quality Selection
- ✅ **AUTOMATIC HIGHEST QUALITY DETECTION**: Enhanced `discover_media_url()` to detect and select the highest quality version when multiple video sources are available on a page.
- ✅ **RESOLUTION-BASED SELECTION**: Automatically selects source with highest resolution (height × width) when resolution attributes are available in HTML.
- ✅ **QUALITY LABEL PARSING**: Extracts resolution from quality labels (e.g., "1080p", "720p") and estimates dimensions for comparison.
- ✅ **FILE SIZE FALLBACK**: When resolution info is unavailable, performs HEAD requests to compare file sizes (larger = higher quality).
- ✅ **MULTIPLE SOURCE DETECTION**: Finds all `<source>` tags in video elements, not just the first one.
- ✅ **INTELLIGENT SORTING**: Prioritizes sources with resolution info, then falls back to file size comparison, ensuring best quality selection.
- ✅ **LOGGING**: Detailed logging shows which source was selected and why (resolution, file size, quality label).

### 🧪 Testing
- ✅ **QUALITY SELECTION TESTS**: Comprehensive test suite covering single source, multiple sources by resolution, quality labels, and fallback behavior.

## Version 0.3.0 - Download History Database & Thumbnails

### 🗄️ Database & Persistence
- ✅ **SQLITE HISTORY DATABASE**: Implemented persistent download history using SQLite database stored in platform-appropriate data directory; all downloads are automatically tracked with full metadata (URL, filename, size, status, timestamps, connections, error messages).
- ✅ **AUTOMATIC TRACKING**: QueueManager now automatically saves downloads to history when added and updates status on completion/failure/cancellation; provides complete audit trail of all download activity.
- ✅ **HISTORY SCHEMA**: Comprehensive database schema with indexed fields for efficient querying by status, date, and URL; includes total_bytes, received_bytes, speed_bps, connections, adaptive mode, created_at, completed_at, and updated_at timestamps.

### 🔍 Search & Filter
- ✅ **ADVANCED FILTERING**: Query history with pagination (limit/offset), status filter (COMPLETED/FAILED/CANCELLED), and full-text search on URLs and filenames; enables quick lookup of past downloads.
- ✅ **AGGREGATE STATISTICS**: Real-time statistics API providing total downloads, completed count, failed count, cancelled count, total bytes across all downloads, and total successfully downloaded bytes.
- ✅ **CLEANUP OPERATIONS**: Manual and automatic cleanup of old history entries with configurable retention period (default 30 days); supports cleanup by status type (e.g., only remove old completed downloads).

### 🌐 API Endpoints
- ✅ **GET /api/history**: Retrieve download history with optional filtering (limit, offset, status, search); returns paginated list of historical downloads.
- ✅ **GET /api/history/statistics**: Get aggregate statistics (total, completed, failed, cancelled, total_bytes, completed_bytes).
- ✅ **GET /api/history/{download_id}**: Retrieve specific download from history by ID.
- ✅ **DELETE /api/history/{download_id}**: Remove specific download from history database.
- ✅ **POST /api/history/clear**: Clear old downloads from history with configurable age threshold (default 30 days) and optional status filter.

### 🎨 UI Enhancements
- ✅ **HISTORY TAB**: Added dedicated History tab in web interface with tab navigation to switch between active Download Queue and historical Downloads.
- ✅ **HISTORY STATISTICS PANEL**: Six-card statistics dashboard showing Total, Completed, Failed, Cancelled downloads, plus Total Size and Downloaded Size with color-coded displays.
- ✅ **SEARCH & FILTER UI**: Search bar for filtering by URL/filename and dropdown filter for status (All/Completed/Failed/Cancelled); real-time filtering updates results instantly.
- ✅ **HISTORY ITEM CARDS**: Each history item displays filename, URL, status badge, file size, downloaded bytes, creation date, completion date, and error message if applicable.
- ✅ **BULK CLEANUP**: "Clear Old (30d+)" button for removing downloads older than 30 days; individual delete buttons for each history item with confirmation dialogs.
- ✅ **DATE FORMATTING**: Human-readable date/time formatting for created_at and completed_at timestamps using browser locale.

### 🧪 Testing
- ✅ **COMPREHENSIVE TEST SUITE**: Added 15 tests covering all history database operations (add, update, delete, query, statistics, cleanup) with 100% pass rate.
- ✅ **DATABASE INITIALIZATION**: Tests for schema creation and database initialization in temporary directories.
- ✅ **CRUD OPERATIONS**: Tests for create, read, update, delete operations with both success and error cases.
- ✅ **FILTERING & SEARCH**: Tests for pagination, status filtering, and text search functionality.
- ✅ **STATISTICS ACCURACY**: Tests verifying correct aggregation of download counts and byte totals.
- ✅ **CLEANUP LOGIC**: Tests for time-based cleanup with configurable retention periods and status filtering.

### 🏗️ Architecture
- ✅ **DOWNLOADHISTORY CLASS**: New downloader/history.py module with comprehensive SQLite database management; handles all database operations with proper error handling and logging.
- ✅ **QUEUEMANAGER INTEGRATION**: History database instance created on QueueManager initialization; automatic tracking on add_download(), on_finished(), and cancel_download().
- ✅ **PLATFORM-APPROPRIATE STORAGE**: Database stored in user data directory using platformdirs (e.g., Windows: AppData\Local, Linux: ~/.local/share, macOS: ~/Library/Application Support).
- ✅ **INDEXED QUERIES**: Database indexes on status, created_at, and url fields for fast filtering and search operations.
- ✅ **DATABASE PATH DISPLAY**: Added GET /api/history/db-path endpoint and UI display showing the database file location; users can open the SQLite file directly with any SQLite viewer for advanced inspection or export.
- ✅ **ENHANCED FILENAME TRACKING**: Database now tracks both `url_filename` (extracted from URL) and `filename` (actual saved filename); automatically extracts filename from URL path when adding downloads.
- ✅ **FILE EXISTENCE TRACKING**: Added `file_exists` column to track whether downloaded files still exist at their save location; automatically checked when retrieving history items.
- ✅ **ACTUAL FILENAME DISPLAY**: History now displays the actual saved filename (extracted from file path) rather than URL filename; automatically updates when file is renamed during download.
- ✅ **REDOWNLOAD FOR ALL ITEMS**: Redownload button now available for all history items (not just completed); preserves original save location and settings when redownloading.
- ✅ **THUMBNAIL EXTRACTION FIXES**: Fixed thumbnail extraction to handle files renamed from `download.bin` to final filename; improved error handling and logging; thumbnails now extracted in separate thread to avoid blocking.
- ✅ **FILE RENAME DETECTION**: Automatically detects when files are renamed after download completion and updates history with correct path; ensures thumbnails are extracted from actual file location.
- ✅ **VIDEO THUMBNAIL EXTRACTION**: Automatic thumbnail extraction from completed video downloads using ffmpeg; extracts frame at 1 second mark, scales to 320px width, saves as JPG alongside video file; thumbnail path stored in database for display in history.
- ✅ **THUMBNAIL DISPLAY IN HISTORY**: History items now display video thumbnails (128x80px) when available; thumbnails load via GET /api/history/{id}/thumbnail endpoint; graceful fallback if thumbnail missing or extraction failed.
- ✅ **REDOWNLOAD FROM HISTORY**: Added POST /api/history/{id}/redownload endpoint to queue downloads from history; preserves original URL, filename, connections, and adaptive settings; automatically switches to Download Queue view after queuing.
- ✅ **REDOWNLOAD BUTTON**: Redownload button now available for all history items (not just completed); clicking queues the download and switches to queue view; enables easy re-downloading of previously completed files.

- ✅ **WINDOWS INSTALLER SYSTEM**: Created complete Windows installer build system for easy deployment on Windows 11 Pro; includes PyInstaller configuration, installer stub, and automated build script.
- ✅ **WEB LAUNCHER**: Added `web_launcher.py` as dedicated production entrypoint that runs FastAPI server without reload mode and automatically opens browser.
- ✅ **WINDOWS INSTALL UTILITIES**: Implemented `windows_install_utils.py` with helpers for Program Files/Desktop path resolution, Windows shortcut creation via COM/PowerShell, and frozen executable resource path handling.
- ✅ **FROZEN ASSET RESOLUTION**: Updated `api/main.py` to correctly locate frontend/dist assets when running as PyInstaller frozen executable using sys._MEIPASS.
- ✅ **INSTALLER EXE**: `installer_win.py` copies application to `C:\Program Files\Motherless Downloader`, creates desktop shortcut with icon, provides clear console output, and handles admin permissions gracefully.
- ✅ **AUTOMATED BUILD SCRIPT**: `build_installer.py` automates entire build: checks frontend build status, builds main app exe with PyInstaller, then builds installer exe; includes pre-flight checks and clear success reporting.
- ✅ **BATCH BUILD WRAPPER**: Added `build_installer.bat` for easy Windows command-line building.
- ✅ **PYINSTALLER SPECS**: Created `motherless_app.spec` (bundles web interface) and `installer.spec` (bundles installer with main app) with correct data file inclusion, hidden imports, and icon configuration.
- ✅ **INSTALLER TESTS**: Added `tests/test_windows_install_utils.py` with unit tests for path resolution, frozen state detection, and resource path helpers using mocks to avoid requiring actual Windows APIs.
- ✅ **INSTALLER DOCUMENTATION**: Updated README.md with comprehensive Windows installer instructions including both usage and building from source; reorganized Quick Start section to prioritize Windows installer as Option 1.

