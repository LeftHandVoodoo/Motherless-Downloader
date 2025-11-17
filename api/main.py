"""FastAPI application for Motherless Downloader."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from platformdirs import user_downloads_dir
import json

from .models import (
    DownloadRequest,
    DownloadInfo,
    SettingsUpdate,
    Settings,
)
from .queue_manager import QueueManager


# Global queue manager
queue_manager: QueueManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global queue_manager
    queue_manager = QueueManager(max_concurrent=3)
    yield
    # Cleanup on shutdown
    queue_manager = None


app = FastAPI(
    title="Motherless Downloader API",
    version="0.2.0",
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


# Settings storage (simple in-memory for now)
_settings = Settings(
    download_dir=user_downloads_dir(),
    default_connections=4,
    adaptive_default=True,
)


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


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.0"}


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


@app.get("/api/settings", response_model=Settings)
async def get_settings():
    """Get application settings."""
    return _settings


@app.patch("/api/settings", response_model=Settings)
async def update_settings(update: SettingsUpdate):
    """Update application settings."""
    global _settings

    if update.download_dir is not None:
        _settings.download_dir = update.download_dir
    if update.default_connections is not None:
        _settings.default_connections = update.default_connections
    if update.adaptive_default is not None:
        _settings.adaptive_default = update.adaptive_default

    return _settings


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time progress updates."""
    await ws_manager.connect(websocket)

    # Register progress callback
    async def progress_callback(download_info: DownloadInfo):
        await ws_manager.broadcast({
            "type": "progress",
            "data": download_info.dict()
        })

    if queue_manager:
        queue_manager.register_progress_callback(progress_callback)

    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            # Echo back for testing
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# Serve frontend static files in production (after building)
# Uncomment when frontend is built
# frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
# if frontend_dist.exists():
#     app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
