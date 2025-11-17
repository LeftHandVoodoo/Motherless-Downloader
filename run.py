#!/usr/bin/env python3
"""Startup script for Motherless Downloader web interface."""
import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def main():
    """Start the FastAPI backend server."""
    print("🚀 Starting Motherless Downloader...")
    print("=" * 60)

    # Start FastAPI backend
    print("\n📡 Starting backend server on http://localhost:8000")
    print("   API docs available at http://localhost:8000/docs")

    try:
        # Run uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn",
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
        return 1

if __name__ == "__main__":
    sys.exit(main())
