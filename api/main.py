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
from platformdirs import user_downloads_dir, user_config_dir

from .models import (
    DownloadRequest,
    DownloadInfo,
    SettingsUpdate,
    Settings,
)
from .queue_manager import QueueManager
from downloader.utils import is_valid_url

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
    version="0.2.2",
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
    return {"status": "ok", "version": "0.2.2"}


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
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
