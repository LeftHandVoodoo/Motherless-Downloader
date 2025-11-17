"""Pydantic models for API requests and responses."""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DownloadStatus(str, Enum):
    """Download status enum."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadRequest(BaseModel):
    """Request to start a new download."""
    url: str = Field(..., description="URL to download")
    filename: Optional[str] = Field(None, description="Optional explicit filename")
    connections: int = Field(4, ge=1, le=30, description="Number of parallel connections")
    adaptive: bool = Field(True, description="Enable adaptive connection management")


class DownloadInfo(BaseModel):
    """Information about a download."""
    id: str = Field(..., description="Unique download ID")
    url: str
    filename: Optional[str] = None
    dest_path: str
    status: DownloadStatus
    total_bytes: int = 0
    received_bytes: int = 0
    speed_bps: float = 0.0
    connections: int = 4
    adaptive: bool = True
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class DownloadProgress(BaseModel):
    """Real-time progress update."""
    id: str
    received_bytes: int
    total_bytes: int
    speed_bps: float
    status: DownloadStatus


class SettingsUpdate(BaseModel):
    """Update application settings."""
    download_dir: Optional[str] = None
    default_connections: Optional[int] = Field(None, ge=1, le=30)
    adaptive_default: Optional[bool] = None


class Settings(BaseModel):
    """Application settings."""
    download_dir: str
    default_connections: int = 4
    adaptive_default: bool = True
