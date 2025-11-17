#!/usr/bin/env python3
"""Startup script for Motherless Downloader web interface."""
import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def get_python_executable():
    """Get the Python executable, preferring venv if available."""
    venv_python = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def main():
    """Start the FastAPI backend server."""
    print("🚀 Starting Motherless Downloader...")
    print("=" * 60)

    # Check if frontend is built
    frontend_dist = Path(__file__).parent / "frontend" / "dist"
    if not frontend_dist.exists():
        print("\n⚠️  Warning: Frontend not built!")
        print("   Run: cd frontend && npm install && npm run build")
        print("   Continuing anyway (API will work, but web UI may not)...\n")

    # Start FastAPI backend
    print("\n📡 Starting backend server on http://localhost:8000")
    print("   Web interface: http://localhost:8000")
    print("   API docs: http://localhost:8000/docs")
    print("\n   Press CTRL+C to stop the server\n")

    python_exe = get_python_executable()
    
    try:
        # Open browser after a short delay
        def open_browser():
            time.sleep(2)  # Wait for server to start
            webbrowser.open("http://localhost:8000")
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Run uvicorn
        subprocess.run([
            python_exe, "-m", "uvicorn",
            "api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        print(f"   Python executable: {python_exe}")
        print(f"   Make sure dependencies are installed: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
