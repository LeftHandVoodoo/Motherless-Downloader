#!/usr/bin/env python3
"""Restart the Motherless Downloader web server."""
import subprocess
import sys
import time
from pathlib import Path

def get_python_executable():
    """Get the Python executable, preferring venv if available."""
    venv_python = Path(__file__).parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def kill_process_on_port(port: int) -> bool:
    """Kill any process listening on the specified port (Windows)."""
    try:
        # Find process using the port
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False
        )
        
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        print(f"Stopping process {pid} on port {port}...")
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True,
                            check=False
                        )
                        return True
                    except Exception as e:
                        print(f"Warning: Could not kill process {pid}: {e}")
        return False
    except Exception as e:
        print(f"Warning: Could not check for processes on port {port}: {e}")
        return False

def main():
    """Restart the server."""
    print("🔄 Restarting Motherless Downloader server...")
    print("=" * 60)
    
    # Kill existing server
    port = 8000
    if kill_process_on_port(port):
        print(f"✅ Stopped existing server on port {port}")
        time.sleep(1)  # Give it a moment to fully stop
    else:
        print(f"ℹ️  No existing server found on port {port}")
    
    # Start new server
    print(f"\n🚀 Starting server on http://localhost:{port}")
    print("   Press CTRL+C to stop\n")
    
    python_exe = get_python_executable()
    
    try:
        subprocess.run([
            python_exe, "-m", "uvicorn",
            "api.main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

