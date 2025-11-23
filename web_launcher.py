#!/usr/bin/env python3
"""Launcher for the Motherless Downloader web interface (production mode)."""
from __future__ import annotations

import sys
import time
import webbrowser
import threading
from pathlib import Path

import uvicorn


def open_browser_delayed(url: str, delay: float = 2.0):
    """Open browser after a delay to allow server startup."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser: {e}")


def main():
    """Start the FastAPI web interface in production mode."""
    print("🚀 Starting Motherless Downloader Web Interface...")
    print("=" * 60)
    
    # Check if frontend is built
    from windows_install_utils import get_resource_path, is_frozen
    
    if is_frozen():
        # When frozen, frontend should be bundled
        frontend_dist = get_resource_path("frontend/dist")
    else:
        # In development, check regular location
        frontend_dist = Path(__file__).parent / "frontend" / "dist"
    
    if not frontend_dist.exists():
        print("\n⚠️  Warning: Frontend not built!")
        print("   The web interface may not work correctly.")
        print("   Please build the frontend first: cd frontend && npm run build\n")
    
    # Start browser in background thread
    print("\n📡 Starting web server on http://localhost:8000")
    print("   Opening browser automatically...")
    print("\n   Press CTRL+C to stop the server\n")
    
    browser_thread = threading.Thread(
        target=open_browser_delayed,
        args=("http://localhost:8000",),
        daemon=True
    )
    browser_thread.start()
    
    try:
        # Run uvicorn without reload (production mode)
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True,
        )
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

