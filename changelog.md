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

