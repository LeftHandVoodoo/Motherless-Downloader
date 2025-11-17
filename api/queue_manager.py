"""Download queue manager for handling multiple concurrent downloads."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Callable
from platformdirs import user_downloads_dir

from downloader.manager import DownloadManager, DownloadRequest as DLRequest
from .models import DownloadStatus, DownloadInfo


class DownloadTask:
    """Represents a single download task."""

    def __init__(
        self,
        url: str,
        dest_dir: str,
        filename: Optional[str] = None,
        connections: int = 4,
        adaptive: bool = True
    ):
        self.id = str(uuid.uuid4())
        self.url = url
        self.dest_dir = dest_dir
        self.filename = filename
        self.connections = connections
        self.adaptive = adaptive
        self.status = DownloadStatus.QUEUED

        self.total_bytes = 0
        self.received_bytes = 0
        self.speed_bps = 0.0
        self.error_message: Optional[str] = None
        self.created_at = datetime.utcnow().isoformat()
        self.completed_at: Optional[str] = None

        self.manager: Optional[DownloadManager] = None
        self.dest_path: Optional[Path] = None

    def to_info(self) -> DownloadInfo:
        """Convert to DownloadInfo model."""
        return DownloadInfo(
            id=self.id,
            url=self.url,
            filename=self.filename or "",
            dest_path=str(self.dest_path) if self.dest_path else self.dest_dir,
            status=self.status,
            total_bytes=self.total_bytes,
            received_bytes=self.received_bytes,
            speed_bps=self.speed_bps,
            connections=self.connections,
            adaptive=self.adaptive,
            error_message=self.error_message,
            created_at=self.created_at,
            completed_at=self.completed_at,
        )


class QueueManager:
    """Manages a queue of downloads with concurrency control."""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, DownloadTask] = {}
        self.active_downloads: set[str] = set()
        self.progress_callbacks: list[Callable] = []
        self._queue_lock = asyncio.Lock()

    def register_progress_callback(self, callback: Callable):
        """Register a callback for progress updates."""
        self.progress_callbacks.append(callback)

    async def add_download(
        self,
        url: str,
        dest_dir: Optional[str] = None,
        filename: Optional[str] = None,
        connections: int = 4,
        adaptive: bool = True
    ) -> str:
        """Add a new download to the queue."""
        if dest_dir is None:
            dest_dir = user_downloads_dir()

        task = DownloadTask(url, dest_dir, filename, connections, adaptive)

        async with self._queue_lock:
            self.tasks[task.id] = task

        # Try to start immediately if under concurrency limit
        await self._process_queue()

        return task.id

    async def _process_queue(self):
        """Process queued downloads up to max concurrency."""
        async with self._queue_lock:
            # Find queued tasks
            queued = [t for t in self.tasks.values() if t.status == DownloadStatus.QUEUED]

            # Start downloads up to max_concurrent
            available_slots = self.max_concurrent - len(self.active_downloads)
            for task in queued[:available_slots]:
                asyncio.create_task(self._start_download(task))

    async def _start_download(self, task: DownloadTask):
        """Start a download task."""
        task.status = DownloadStatus.DOWNLOADING
        self.active_downloads.add(task.id)
        await self._notify_progress(task)

        # Create download request
        dest_path = Path(task.dest_dir) / (task.filename or "download.bin")
        request = DLRequest(
            url=task.url,
            dest_file=dest_path,
            explicit_filename=task.filename,
            connections=task.connections,
            adaptive_connections=task.adaptive,
        )

        # Create manager with signal connections
        manager = DownloadManager(request)
        task.manager = manager
        task.dest_path = dest_path

        # Connect signals
        def on_progress(received: int, total: int):
            task.received_bytes = received
            task.total_bytes = total
            # Schedule async notification
            asyncio.create_task(self._notify_progress(task))

        def on_speed(bps: float):
            task.speed_bps = bps
            asyncio.create_task(self._notify_progress(task))

        def on_finished(success: bool, message: str):
            if success:
                task.status = DownloadStatus.COMPLETED
                task.completed_at = datetime.utcnow().isoformat()
            else:
                task.status = DownloadStatus.FAILED
                task.error_message = message

            self.active_downloads.discard(task.id)
            asyncio.create_task(self._notify_progress(task))
            asyncio.create_task(self._process_queue())

        manager.progress.connect(on_progress)
        manager.speed.connect(on_speed)
        manager.finished.connect(on_finished)

        # Start download in thread
        manager.start()

    async def _notify_progress(self, task: DownloadTask):
        """Notify all registered callbacks of progress."""
        for callback in self.progress_callbacks:
            try:
                await callback(task.to_info())
            except Exception:
                pass

    def get_download(self, download_id: str) -> Optional[DownloadInfo]:
        """Get download info by ID."""
        task = self.tasks.get(download_id)
        return task.to_info() if task else None

    def get_all_downloads(self) -> list[DownloadInfo]:
        """Get all downloads."""
        return [task.to_info() for task in self.tasks.values()]

    async def pause_download(self, download_id: str) -> bool:
        """Pause a download."""
        task = self.tasks.get(download_id)
        if task and task.manager and task.status == DownloadStatus.DOWNLOADING:
            task.manager.pause()
            task.status = DownloadStatus.PAUSED
            await self._notify_progress(task)
            return True
        return False

    async def resume_download(self, download_id: str) -> bool:
        """Resume a paused download."""
        task = self.tasks.get(download_id)
        if task and task.manager and task.status == DownloadStatus.PAUSED:
            task.manager.resume()
            task.status = DownloadStatus.DOWNLOADING
            await self._notify_progress(task)
            return True
        return False

    async def cancel_download(self, download_id: str) -> bool:
        """Cancel a download."""
        task = self.tasks.get(download_id)
        if task and task.manager:
            task.manager.cancel()
            task.status = DownloadStatus.CANCELLED
            self.active_downloads.discard(download_id)
            await self._notify_progress(task)
            await self._process_queue()
            return True
        return False

    async def remove_download(self, download_id: str) -> bool:
        """Remove a download from the queue."""
        async with self._queue_lock:
            if download_id in self.tasks:
                task = self.tasks[download_id]
                if task.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED):
                    await self.cancel_download(download_id)
                del self.tasks[download_id]
                return True
        return False
