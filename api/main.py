"""FastAPI application for Motherless Downloader."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from platformdirs import user_downloads_dir, user_config_dir
import subprocess
import shutil
import platform

from .models import (
    DownloadRequest,
    DownloadInfo,
    SettingsUpdate,
    Settings,
)
from .queue_manager import QueueManager
from downloader.utils import is_valid_url
from downloader.thumbnail import extract_thumbnail

# Configure logging - set to DEBUG for thumbnail debugging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see thumbnail extraction logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True  # Force reconfiguration
)

# Set specific loggers to appropriate levels
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("downloader.thumbnail").setLevel(logging.DEBUG)
logging.getLogger("api.queue_manager").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


# Global queue manager
queue_manager: QueueManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global queue_manager
    queue_manager = QueueManager(max_concurrent=3)
    # Set the event loop for thread-safe async scheduling
    queue_manager.set_event_loop(asyncio.get_running_loop())
    yield
    # Cleanup on shutdown
    queue_manager = None


app = FastAPI(
    title="Motherless Downloader API",
    version="0.3.2",
    lifespan=lifespan
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Settings file path
_settings_file = Path(user_config_dir("motherless-downloader")) / "settings.json"


def load_settings() -> Settings:
    """Load settings from file or return defaults."""
    if _settings_file.exists():
        try:
            with open(_settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Settings(**data)
        except Exception:
            pass
    
    # Default settings
    return Settings(
        download_dir=user_downloads_dir(),
        default_connections=4,
        adaptive_default=True,
    )


def save_settings(settings: Settings) -> None:
    """Save settings to file using atomic write to prevent corruption."""
    import tempfile
    import os
    
    _settings_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Atomic write: write to temp file, then rename
    fd, tmp_path_str = tempfile.mkstemp(prefix=_settings_file.name, dir=str(_settings_file.parent))
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings.dict(), f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, _settings_file)
    except Exception as e:
        # Clean up temp file on error
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise


# Load settings on startup
_settings = load_settings()


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


ws_manager = ConnectionManager()


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.3.2"}


@app.post("/api/test-thumbnail")
async def test_thumbnail(data: dict):
    """Test thumbnail extraction on a file path."""
    file_path = data.get("path")
    if not file_path:
        raise HTTPException(400, "path parameter required")
    
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(404, f"File not found: {file_path}")
    
    logger.info(f"Testing thumbnail extraction for: {path}")
    logger.info(f"File extension: {path.suffix}")
    logger.info(f"File exists: {path.exists()}")
    logger.info(f"File size: {path.stat().st_size if path.exists() else 0}")
    
    # Use download directory (parent of file) for thumbnail cache
    download_dir = path.parent
    result = extract_thumbnail(path, download_dir=download_dir)
    
    if result:
        return {
            "success": True,
            "thumbnail_path": str(result),
            "exists": result.exists(),
            "size": result.stat().st_size if result.exists() else 0
        }
    else:
        return {
            "success": False,
            "message": "Thumbnail extraction returned None (check server logs for details)",
            "file_extension": path.suffix,
            "file_exists": path.exists()
        }


@app.get("/api/debug/recent-downloads")
async def get_recent_downloads_info():
    """Get information about recent downloads for debugging."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    # Get recent history items
    recent = queue_manager.history.get_all_downloads(limit=10, offset=0)
    
    debug_info = []
    for item in recent:
        debug_info.append({
            "id": item["id"],
            "filename": item.get("filename"),
            "dest_path": item.get("dest_path"),
            "status": item.get("status"),
            "thumbnail_path": item.get("thumbnail_path"),
            "file_exists": Path(item.get("dest_path", "")).exists() if item.get("dest_path") else False,
            "thumbnail_exists": Path(item.get("thumbnail_path", "")).exists() if item.get("thumbnail_path") else False,
            "completed_at": item.get("completed_at")
        })
    
    return {"recent_downloads": debug_info}


@app.get("/api/downloads", response_model=List[DownloadInfo])
async def get_downloads():
    """Get all downloads."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    return queue_manager.get_all_downloads()


@app.get("/api/downloads/{download_id}", response_model=DownloadInfo)
async def get_download(download_id: str):
    """Get a specific download."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")

    download = queue_manager.get_download(download_id)
    if not download:
        raise HTTPException(404, "Download not found")
    return download


@app.post("/api/downloads", response_model=dict)
async def create_download(request: DownloadRequest):
    """Create a new download."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")

    # Validate URL before adding to queue
    if not is_valid_url(request.url):
        raise HTTPException(400, "Invalid URL: Must be HTTPS and from allowed domains")

    download_id = await queue_manager.add_download(
        url=request.url,
        dest_dir=_settings.download_dir,
        filename=request.filename,
        connections=request.connections,
        adaptive=request.adaptive,
    )

    return {"id": download_id}


@app.post("/api/downloads/{download_id}/pause")
async def pause_download(download_id: str):
    """Pause a download."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")

    success = await queue_manager.pause_download(download_id)
    if not success:
        raise HTTPException(400, "Could not pause download")
    return {"status": "paused"}


@app.post("/api/downloads/{download_id}/resume")
async def resume_download(download_id: str):
    """Resume a paused download."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")

    success = await queue_manager.resume_download(download_id)
    if not success:
        raise HTTPException(400, "Could not resume download")
    return {"status": "resumed"}


@app.post("/api/downloads/{download_id}/cancel")
async def cancel_download(download_id: str):
    """Cancel a download."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")

    success = await queue_manager.cancel_download(download_id)
    if not success:
        raise HTTPException(400, "Could not cancel download")
    return {"status": "cancelled"}


@app.delete("/api/downloads/{download_id}")
async def remove_download(download_id: str):
    """Remove a download from the queue."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")

    success = await queue_manager.remove_download(download_id)
    if not success:
        raise HTTPException(404, "Download not found")
    return {"status": "removed"}


@app.post("/api/downloads/cleanup")
async def cleanup_completed():
    """Clean up old completed/failed/cancelled downloads."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")

    removed_count = await queue_manager.cleanup_completed()
    return {"removed": removed_count, "status": "ok"}


@app.get("/api/history")
async def get_history(
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
    search: str | None = None
):
    """Get download history with optional filtering."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    history_items = queue_manager.history.get_all_downloads(
        limit=limit,
        offset=offset,
        status=status,
        search=search
    )
    return {"items": history_items, "limit": limit, "offset": offset}


@app.get("/api/history/statistics")
async def get_history_statistics():
    """Get aggregate statistics about download history."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    return queue_manager.history.get_statistics()


@app.get("/api/history/db-path")
async def get_history_db_path():
    """Get the path to the history database file."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    return {
        "path": str(queue_manager.history.db_path),
        "exists": queue_manager.history.db_path.exists()
    }


@app.post("/api/history/clear")
async def clear_old_history(days: int = 30, status: str | None = None):
    """Clear old downloads from history."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    if days < 1:
        raise HTTPException(400, "Days must be at least 1")
    
    removed_count = queue_manager.history.clear_old_downloads(days=days, status=status)
    return {"removed": removed_count, "status": "ok"}


@app.get("/api/history/{download_id}")
async def get_history_item(download_id: str):
    """Get a specific download from history."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    item = queue_manager.history.get_download(download_id)
    if not item:
        raise HTTPException(404, "Download not found in history")
    return item


@app.delete("/api/history/{download_id}")
async def delete_history_item(download_id: str):
    """Delete a specific download from history."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    success = queue_manager.history.delete_download(download_id)
    if not success:
        raise HTTPException(404, "Download not found in history")
    return {"status": "deleted"}


@app.post("/api/history/{download_id}/redownload")
async def redownload_from_history(download_id: str):
    """Redownload a file from history."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    # Get download info from history
    history_item = queue_manager.history.get_download(download_id)
    if not history_item:
        raise HTTPException(404, "Download not found in history")
    
    # Validate URL
    if not is_valid_url(history_item["url"]):
        raise HTTPException(400, "Invalid URL in history")
    
    # Use original dest_dir if available, otherwise use current download_dir
    dest_dir = None
    if history_item.get("dest_path"):
        dest_dir = str(Path(history_item["dest_path"]).parent)
    else:
        dest_dir = _settings.download_dir
    
    # Add to download queue
    new_download_id = await queue_manager.add_download(
        url=history_item["url"],
        dest_dir=dest_dir,
        filename=None,  # Let it auto-detect filename
        connections=history_item.get("connections", 4),
        adaptive=history_item.get("adaptive", True),
    )
    
    return {"id": new_download_id, "status": "queued"}


@app.get("/api/history/{download_id}/thumbnail")
async def get_history_thumbnail(download_id: str):
    """Get thumbnail image for a history item."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    history_item = queue_manager.history.get_download(download_id)
    if not history_item:
        raise HTTPException(404, "Download not found in history")
    
    thumbnail_path = history_item.get("thumbnail_path")
    if not thumbnail_path:
        raise HTTPException(404, "Thumbnail not available")
    
    thumb_path = Path(thumbnail_path)
    if not thumb_path.exists():
        raise HTTPException(404, "Thumbnail file not found")
    
    return FileResponse(thumb_path, media_type="image/jpeg")


def find_vlc_executable() -> str | None:
    """Find VLC executable path."""
    system = platform.system()
    
    if system == "Windows":
        # Common VLC installation paths on Windows
        possible_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\VideoLAN\VLC media player.lnk",
        ]
        # Also check if vlc is in PATH
        vlc_in_path = shutil.which("vlc")
        if vlc_in_path:
            return vlc_in_path
        
        for path in possible_paths:
            if Path(path).exists():
                return path
    elif system == "Darwin":  # macOS
        possible_paths = [
            "/Applications/VLC.app/Contents/MacOS/VLC",
            "/usr/local/bin/vlc",
        ]
        vlc_in_path = shutil.which("vlc")
        if vlc_in_path:
            return vlc_in_path
        
        for path in possible_paths:
            if Path(path).exists():
                return path
    else:  # Linux
        vlc_in_path = shutil.which("vlc")
        if vlc_in_path:
            return vlc_in_path
        # Try common Linux paths
        possible_paths = ["/usr/bin/vlc", "/usr/local/bin/vlc"]
        for path in possible_paths:
            if Path(path).exists():
                return path
    
    return None


@app.post("/api/history/{download_id}/open")
async def open_file_in_vlc(download_id: str):
    """Open the downloaded file in VLC media player."""
    if not queue_manager:
        raise HTTPException(500, "Queue manager not initialized")
    
    history_item = queue_manager.history.get_download(download_id)
    if not history_item:
        raise HTTPException(404, "Download not found in history")
    
    dest_path = history_item.get("dest_path")
    if not dest_path:
        raise HTTPException(404, "File path not available")
    
    file_path = Path(dest_path)
    if not file_path.exists():
        raise HTTPException(404, f"File not found: {dest_path}")
    
    # Find VLC executable
    vlc_path = find_vlc_executable()
    if not vlc_path:
        raise HTTPException(500, "VLC not found. Please install VLC media player.")
    
    try:
        # Launch VLC with the file
        subprocess.Popen([vlc_path, str(file_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"Opened file in VLC: {file_path}")
        return JSONResponse({"status": "opened", "file": str(file_path)})
    except Exception as e:
        logger.error(f"Failed to open file in VLC: {e}")
        raise HTTPException(500, f"Failed to open file in VLC: {e}")


@app.get("/api/settings", response_model=Settings)
async def get_settings():
    """Get application settings."""
    return _settings


@app.post("/api/settings/validate-dir")
async def validate_directory(data: dict):
    """Validate that a directory path exists and is accessible."""
    path = data.get("path", "")
    if not path:
        return {"valid": False, "error": "No path provided"}
    
    try:
        dir_path = Path(path)
        if not dir_path.exists():
            return {"valid": False, "error": "Directory does not exist"}
        if not dir_path.is_dir():
            return {"valid": False, "error": "Path is not a directory"}
        # Check if we can write to it
        try:
            test_file = dir_path / ".test_write"
            test_file.touch()
            test_file.unlink()
            return {"valid": True, "path": str(dir_path.resolve())}
        except PermissionError:
            return {"valid": False, "error": "No write permission to directory"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@app.patch("/api/settings", response_model=Settings)
async def update_settings(update: SettingsUpdate):
    """Update application settings."""
    global _settings

    if update.download_dir is not None:
        # Validate the directory path
        dir_path = Path(update.download_dir)
        if not dir_path.exists():
            raise HTTPException(400, f"Directory does not exist: {update.download_dir}")
        if not dir_path.is_dir():
            raise HTTPException(400, f"Path is not a directory: {update.download_dir}")
        _settings.download_dir = str(dir_path.resolve())
    if update.default_connections is not None:
        _settings.default_connections = update.default_connections
    if update.adaptive_default is not None:
        _settings.adaptive_default = update.adaptive_default

    # Persist settings to file
    save_settings(_settings)

    return _settings


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await ws_manager.connect(websocket)
    callback_id = None

    # Register progress callback
    async def progress_callback(download_info: DownloadInfo):
        logger.debug(f"Broadcasting progress via WebSocket: {download_info.id}")
        await ws_manager.broadcast({
            "type": "progress",
            "data": download_info.dict()
        })

    if queue_manager:
        callback_id = queue_manager.register_progress_callback(progress_callback)
        logger.info(f"Registered progress callback {callback_id} for WebSocket")
    else:
        logger.error("Queue manager not available!")

    try:
        while True:
            # Handle client messages
            try:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")
                    
                    if msg_type == "ping":
                        # Respond to ping with pong
                        await websocket.send_json({"type": "pong"})
                    elif msg_type == "get_status":
                        # Send current download status
                        if queue_manager:
                            downloads = await queue_manager.get_all_downloads()
                            await websocket.send_json({
                                "type": "status",
                                "data": [d.dict() for d in downloads]
                            })
                    else:
                        logger.debug(f"Unknown WebSocket message type: {msg_type}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in WebSocket message: {data}")
            except (WebSocketDisconnect, RuntimeError) as e:
                # RuntimeError can occur when trying to receive after disconnect
                if "disconnect" in str(e).lower() or isinstance(e, WebSocketDisconnect):
                    logger.info("WebSocket client disconnected")
                    break
                else:
                    logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except RuntimeError as e:
        # Handle RuntimeError from disconnected WebSocket
        if "disconnect" in str(e).lower():
            logger.info("WebSocket client disconnected (RuntimeError)")
        else:
            logger.error(f"WebSocket RuntimeError: {e}", exc_info=True)
    finally:
        ws_manager.disconnect(websocket)
        # Unregister callback to prevent memory leak
        if queue_manager and callback_id is not None:
            queue_manager.unregister_progress_callback(callback_id)
            logger.info(f"Unregistered progress callback {callback_id}")


# Serve frontend static files in production (after building)
# Handle both development and frozen (PyInstaller) modes
import sys

if getattr(sys, "frozen", False):
    # Running as frozen executable - use resource path helper
    try:
        from windows_install_utils import get_resource_path
        frontend_dist = get_resource_path("frontend/dist")
    except ImportError:
        # Fallback if helper not available
        frontend_dist = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    # Running in development
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
