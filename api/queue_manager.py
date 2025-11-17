"""Download queue manager for handling multiple concurrent downloads."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Callable
from platformdirs import user_downloads_dir

from downloader.manager import DownloadManager, DownloadRequest as DLRequest
from downloader.history import DownloadHistory
from downloader.thumbnail import extract_thumbnail
from .models import DownloadStatus, DownloadInfo

logger = logging.getLogger(__name__)


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
        self.last_progress_update = 0.0  # Timestamp for throttling

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
    
    def to_history_dict(self) -> dict:
        """Convert to dictionary for history database."""
        from urllib.parse import urlparse
        parsed = urlparse(self.url)
        url_filename = Path(parsed.path).name if parsed.path else None
        
        return {
            "id": self.id,
            "url": self.url,
            "filename": self.filename or "",
            "url_filename": url_filename,
            "dest_path": str(self.dest_path) if self.dest_path else self.dest_dir,
            "status": self.status.value,
            "total_bytes": self.total_bytes,
            "received_bytes": self.received_bytes,
            "speed_bps": self.speed_bps,
            "connections": self.connections,
            "adaptive": self.adaptive,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class QueueManager:
    """Manages a queue of downloads with concurrency control."""

    def __init__(self, max_concurrent: int = 3, auto_cleanup_hours: int = 24, max_completed: int = 100):
        self.max_concurrent = max_concurrent
        self.auto_cleanup_hours = auto_cleanup_hours
        self.max_completed = max_completed
        self.tasks: Dict[str, DownloadTask] = {}
        self.active_downloads: set[str] = set()
        self.progress_callbacks: Dict[int, Callable] = {}  # Use dict with callback ID
        self._callback_counter = 0
        self._queue_lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.PROGRESS_THROTTLE_INTERVAL = 0.5  # seconds between updates
        self._cleanup_task: Optional[asyncio.Task] = None
        self.history = DownloadHistory()  # Initialize download history database

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the asyncio event loop for thread-safe task scheduling."""
        self._loop = loop
        # Start periodic cleanup task
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("Started periodic cleanup task")

    def register_progress_callback(self, callback: Callable) -> int:
        """Register a callback for progress updates. Returns callback ID."""
        self._callback_counter += 1
        callback_id = self._callback_counter
        self.progress_callbacks[callback_id] = callback
        logger.info(f"Registered progress callback {callback_id}")
        return callback_id

    def unregister_progress_callback(self, callback_id: int):
        """Unregister a progress callback by ID."""
        if callback_id in self.progress_callbacks:
            del self.progress_callbacks[callback_id]
            logger.info(f"Unregistered progress callback {callback_id}")

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
        
        # Add to history database
        self.history.add_download(task.to_history_dict())
        logger.debug(f"Added download {task.id} to history database")

        # Try to start immediately if under concurrency limit
        await self._process_queue()

        return task.id

    async def _process_queue(self):
        """Process queued downloads up to max concurrency."""
        tasks_to_start = []

        async with self._queue_lock:
            # Find queued tasks
            queued = [t for t in self.tasks.values() if t.status == DownloadStatus.QUEUED]

            # Start downloads up to max_concurrent
            available_slots = self.max_concurrent - len(self.active_downloads)
            for task in queued[:available_slots]:
                # Mark as starting and add to active set BEFORE releasing lock
                # This prevents race condition where multiple _process_queue calls
                # could start more downloads than max_concurrent
                task.status = DownloadStatus.DOWNLOADING
                self.active_downloads.add(task.id)
                tasks_to_start.append(task)

        # Start downloads outside the lock to avoid blocking
        for task in tasks_to_start:
            asyncio.create_task(self._start_download(task))

    async def _start_download(self, task: DownloadTask):
        """Start a download task.

        Note: Task status and active_downloads are already set by _process_queue
        before this is called, to prevent race conditions.
        """
        try:
            # Notify that download is starting
            await self._notify_progress(task, force=True)

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
                # Throttle progress updates to avoid WebSocket flooding
                current_time = time.time()
                if current_time - task.last_progress_update >= self.PROGRESS_THROTTLE_INTERVAL:
                    task.last_progress_update = current_time
                    if self._loop:
                        asyncio.run_coroutine_threadsafe(self._notify_progress(task), self._loop)

            def on_speed(bps: float):
                task.speed_bps = bps
                # Speed updates are already throttled by progress throttling
                # No need to send separate speed updates

            def on_finished(success: bool, message: str):
                logger.info(f"Download {task.id} finished: success={success}, message={message}")
                thumbnail_path = None
                
                if success:
                    task.status = DownloadStatus.COMPLETED
                    task.completed_at = datetime.utcnow().isoformat()
                    
                    # Update dest_path to actual file (file may have been renamed from download.bin to final name)
                    if task.dest_path and not task.dest_path.exists():
                        # File was renamed - find the actual file
                        dest_dir = task.dest_path.parent
                        if dest_dir.exists():
                            # Look for recently modified files in the directory
                            try:
                                recent_files = sorted(
                                    dest_dir.glob("*"),
                                    key=lambda p: p.stat().st_mtime if p.is_file() else 0,
                                    reverse=True
                                )
                                # Find the first file that's not a part file or sidecar
                                for f in recent_files[:5]:  # Check top 5 most recent
                                    if f.is_file() and not f.name.endswith(('.part', '.part.json')):
                                        # Check if it was modified recently (within last minute)
                                        if time.time() - f.stat().st_mtime < 60:
                                            logger.info(f"Found renamed file for {task.id}: {f.name} (was {task.dest_path.name})")
                                            task.dest_path = f
                                            break
                            except Exception as e:
                                logger.warning(f"Failed to find renamed file for {task.id}: {e}")
                    
                    # Extract thumbnail for video files
                    # Run thumbnail extraction asynchronously to avoid blocking the callback
                    def extract_thumb_async():
                        try:
                            if not task.dest_path:
                                logger.warning(f"Skipping thumbnail extraction for {task.id}: dest_path is None")
                                return
                            
                            if not task.dest_path.exists():
                                logger.warning(f"Skipping thumbnail extraction for {task.id}: file does not exist: {task.dest_path}")
                                return
                            
                            logger.info(f"Attempting thumbnail extraction for {task.id}: {task.dest_path}")
                            logger.info(f"File extension: {task.dest_path.suffix}")
                            logger.info(f"File size: {task.dest_path.stat().st_size:,} bytes")
                            
                            # Update filename in database to actual saved filename
                            if task.dest_path.exists():
                                actual_filename = task.dest_path.name
                                # Normalize the filename (remove random numbers, capitalize appropriately)
                                from downloader.utils import normalize_filename
                                normalized_filename = normalize_filename(actual_filename)
                                # If normalization changed the name, rename the file
                                if normalized_filename != actual_filename:
                                    normalized_path = task.dest_path.parent / normalized_filename
                                    try:
                                        task.dest_path.rename(normalized_path)
                                        task.dest_path = normalized_path
                                        actual_filename = normalized_filename
                                        logger.info(f"Renamed file for {task.id}: {task.dest_path.name} -> {normalized_filename}")
                                    except Exception as e:
                                        logger.warning(f"Failed to rename file for {task.id}: {e}")
                                        # Continue with original filename if rename fails
                                if actual_filename != task.filename:
                                    logger.debug(f"Updating filename for {task.id}: {task.filename} -> {actual_filename}")
                                    if self._loop:
                                        asyncio.run_coroutine_threadsafe(
                                            self._update_filename(task.id, actual_filename),
                                            self._loop
                                        )
                            
                            thumb = extract_thumbnail(task.dest_path)
                            if thumb:
                                thumbnail_path_str = str(thumb)
                                logger.info(f"Successfully extracted thumbnail for {task.id}: {thumbnail_path_str}")
                                # Update history with thumbnail path
                                if self._loop:
                                    try:
                                        asyncio.run_coroutine_threadsafe(
                                            self._update_thumbnail(task.id, thumbnail_path_str),
                                            self._loop
                                        )
                                    except Exception as e:
                                        logger.error(f"Failed to schedule thumbnail update: {e}", exc_info=True)
                            else:
                                logger.warning(f"Thumbnail extraction returned None for {task.id} - check logs above for reason")
                        except Exception as e:
                            logger.error(f"Failed to extract thumbnail for {task.id}: {e}", exc_info=True)
                    
                    # Run thumbnail extraction in a thread to avoid blocking
                    # Use non-daemon thread to ensure it completes
                    import threading
                    thumb_thread = threading.Thread(target=extract_thumb_async, name=f"ThumbExtract-{task.id}")
                    thumb_thread.daemon = False  # Ensure thread completes
                    thumb_thread.start()
                    logger.debug(f"Started thumbnail extraction thread for {task.id}")
                else:
                    task.status = DownloadStatus.FAILED
                    task.error_message = message
                    # Clean up partial files on failure
                    if task.dest_path:
                        part_path = task.dest_path.with_name(task.dest_path.name + ".part")
                        sidecar_path = task.dest_path.with_name(task.dest_path.name + ".part.json")
                        try:
                            part_path.unlink(missing_ok=True)
                            sidecar_path.unlink(missing_ok=True)
                            logger.debug(f"Cleaned up partial files for failed download {task.id}")
                        except Exception as e:
                            logger.warning(f"Failed to clean up partial files for {task.id}: {e}")

                self.active_downloads.discard(task.id)
                
                # Update history database with final status (thumbnail will be updated separately if extraction succeeds)
                # Extract actual filename from path if available
                actual_filename = None
                if task.dest_path and task.dest_path.exists():
                    actual_filename = task.dest_path.name
                elif task.dest_path:
                    # Even if file doesn't exist, use the path name
                    actual_filename = task.dest_path.name
                
                # Normalize filename if we have one
                if actual_filename:
                    from downloader.utils import normalize_filename
                    normalized_filename = normalize_filename(actual_filename)
                    # If normalization changed the name and file exists, try to rename it
                    if normalized_filename != actual_filename and task.dest_path and task.dest_path.exists():
                        normalized_path = task.dest_path.parent / normalized_filename
                        try:
                            task.dest_path.rename(normalized_path)
                            task.dest_path = normalized_path
                            actual_filename = normalized_filename
                            logger.info(f"Renamed file for {task.id} on completion: {task.dest_path.name} -> {normalized_filename}")
                        except Exception as e:
                            logger.warning(f"Failed to rename file for {task.id} on completion: {e}")
                            # Continue with original filename if rename fails
                    elif normalized_filename != actual_filename:
                        # File doesn't exist, but update the stored filename anyway
                        actual_filename = normalized_filename
                
                update_data = {
                    "status": task.status.value,
                    "total_bytes": task.total_bytes,
                    "received_bytes": task.received_bytes,
                    "error_message": task.error_message,
                    "completed_at": task.completed_at,
                    "dest_path": str(task.dest_path) if task.dest_path else task.dest_dir,
                    "filename": actual_filename or task.filename or ""
                }
                
                self.history.update_download(task.id, update_data)
                logger.debug(f"Updated download {task.id} in history database")
                
                # Schedule cleanup asynchronously - don't wait from within the thread's own callback
                if self._loop:
                    asyncio.run_coroutine_threadsafe(self._notify_progress(task, force=True), self._loop)
                    asyncio.run_coroutine_threadsafe(self._process_queue(), self._loop)
                    # Clean up thread asynchronously after a short delay
                    asyncio.run_coroutine_threadsafe(self._cleanup_thread_async(task.id), self._loop)

            # Use Qt.DirectConnection to ensure callbacks fire immediately from worker thread
            from PySide6.QtCore import Qt
            manager.progress.connect(on_progress, Qt.ConnectionType.DirectConnection)
            manager.speed.connect(on_speed, Qt.ConnectionType.DirectConnection)
            manager.finished.connect(on_finished, Qt.ConnectionType.DirectConnection)
            logger.debug(f"Connected signals for task {task.id}")

            # Start download in thread
            manager.start()
            logger.info(f"Started download task {task.id} for {task.url}")

        except Exception as e:
            logger.error(f"Failed to start download {task.id}: {e}", exc_info=True)
            task.status = DownloadStatus.FAILED
            task.error_message = f"Failed to start: {str(e)}"
            self.active_downloads.discard(task.id)
            await self._notify_progress(task, force=True)
            await self._process_queue()

    async def _cleanup_thread_async(self, task_id: str):
        """Clean up QThread asynchronously after download finishes.
        
        This is called from the asyncio event loop, not from within the thread itself,
        preventing "Thread tried to wait on itself" errors.
        """
        await asyncio.sleep(0.5)  # Give thread a moment to finish naturally
        
        # Get task reference (brief lock)
        async with self._queue_lock:
            task = self.tasks.get(task_id)
            if not task or not task.manager:
                return
            manager = task.manager
        
        # Wait for thread outside the lock (blocking, but in thread pool)
        try:
            if manager.isRunning():
                # Request thread to quit
                manager.quit()
                # Run blocking wait in thread pool to avoid blocking event loop
                await asyncio.to_thread(manager.wait, 2000)
        except Exception as e:
            logger.warning(f"Error waiting for thread {task_id}: {e}")
        
        # Clear reference (brief lock)
        async with self._queue_lock:
            task = self.tasks.get(task_id)
            if task:
                task.manager = None
                logger.debug(f"Cleaned up thread for task {task_id}")

    async def _update_filename(self, task_id: str, filename: str):
        """Update history with actual filename after file is saved."""
        try:
            self.history.update_download(task_id, {"filename": filename})
            logger.debug(f"Updated filename for {task_id}: {filename}")
            # Notify clients of the update
            task = self.tasks.get(task_id)
            if task:
                await self._notify_progress(task, force=True)
        except Exception as e:
            logger.error(f"Failed to update filename for {task_id}: {e}", exc_info=True)
    
    async def _update_thumbnail(self, task_id: str, thumbnail_path: str):
        """Update history with thumbnail path after extraction completes."""
        try:
            self.history.update_download(task_id, {"thumbnail_path": thumbnail_path})
            logger.info(f"Updated thumbnail path for {task_id}: {thumbnail_path}")
            # Notify clients of the update
            task = self.tasks.get(task_id)
            if task:
                await self._notify_progress(task, force=True)
        except Exception as e:
            logger.error(f"Failed to update thumbnail path for {task_id}: {e}", exc_info=True)
    
    async def _notify_progress(self, task: DownloadTask, force: bool = False):
        """Notify all registered callbacks of progress.

        Args:
            task: The download task to notify about
            force: If True, bypass throttling (used for important status changes)
        """
        logger.debug(f"Notifying progress: {task.id} - {task.received_bytes}/{task.total_bytes} - status={task.status}")
        for callback_id, callback in list(self.progress_callbacks.items()):
            try:
                await callback(task.to_info())
            except Exception as e:
                logger.error(f"Error in progress callback {callback_id}: {e}", exc_info=True)

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
            task.completed_at = datetime.utcnow().isoformat()
            self.active_downloads.discard(download_id)
            
            # Clean up partial files on cancel
            if task.dest_path:
                part_path = task.dest_path.with_name(task.dest_path.name + ".part")
                sidecar_path = task.dest_path.with_name(task.dest_path.name + ".part.json")
                try:
                    part_path.unlink(missing_ok=True)
                    sidecar_path.unlink(missing_ok=True)
                    logger.info(f"Cleaned up partial files for cancelled download {download_id}")
                except Exception as e:
                    logger.warning(f"Failed to clean up partial files for {download_id}: {e}")
            
            # Update history database
            self.history.update_download(download_id, {
                "status": task.status.value,
                "completed_at": task.completed_at
            })
            logger.debug(f"Updated cancelled download {download_id} in history database")
            
            # Schedule thread cleanup asynchronously (don't wait from async context)
            if self._loop:
                asyncio.run_coroutine_threadsafe(self._cleanup_thread_async(download_id), self._loop)
            
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

    async def cleanup_completed(self) -> int:
        """Clean up old completed/failed/cancelled downloads.
        
        Thread-safe: Uses queue lock to prevent race conditions with active downloads.

        Returns:
            Number of downloads removed
        """
        removed_count = 0
        current_time = datetime.utcnow()

        async with self._queue_lock:
            to_remove = []

            for task_id, task in self.tasks.items():
                # Only consider finished tasks that are not active
                if task.status not in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED):
                    continue
                
                # Double-check: ensure task is not in active_downloads (thread-safe check)
                if task_id in self.active_downloads:
                    logger.warning(f"Skipping cleanup of active download {task_id}")
                    continue

                # Remove if completed_at timestamp is old enough
                if task.completed_at:
                    try:
                        completed_time = datetime.fromisoformat(task.completed_at)
                        age_hours = (current_time - completed_time).total_seconds() / 3600

                        if age_hours >= self.auto_cleanup_hours:
                            to_remove.append(task_id)
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid completed_at timestamp for task {task_id}")

            # Also enforce max completed limit
            completed_tasks = [
                (task_id, task) for task_id, task in self.tasks.items()
                if task.status in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED)
                and task_id not in self.active_downloads  # Thread-safe: exclude active
            ]

            if len(completed_tasks) > self.max_completed:
                # Sort by completion time (oldest first)
                completed_tasks.sort(key=lambda x: x[1].completed_at or x[1].created_at)
                excess = len(completed_tasks) - self.max_completed
                for task_id, _ in completed_tasks[:excess]:
                    if task_id not in to_remove:
                        to_remove.append(task_id)

            # Remove the tasks (still holding lock, so thread-safe)
            for task_id in to_remove:
                # Final safety check before deletion
                if task_id not in self.active_downloads:
                    task = self.tasks.get(task_id)
                    if task:
                        # Clean up thread if still exists
                        if task.manager:
                            try:
                                if task.manager.isRunning():
                                    task.manager.wait(1000)  # Wait up to 1 second
                                task.manager = None
                            except Exception as e:
                                logger.warning(f"Error cleaning up thread for {task_id} during cleanup: {e}")
                        del self.tasks[task_id]
                        removed_count += 1
                else:
                    logger.warning(f"Skipping removal of active download {task_id}")

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old downloads")

        return removed_count

    async def _periodic_cleanup(self):
        """Periodic cleanup task that runs every hour with resilience."""
        retry_count = 0
        max_retries = 3
        
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                try:
                    cleaned = await self.cleanup_completed()
                    if cleaned > 0:
                        logger.info(f"Periodic cleanup removed {cleaned} old downloads")
                    retry_count = 0  # Reset on success
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error in periodic cleanup (attempt {retry_count}/{max_retries}): {e}", exc_info=True)
                    if retry_count >= max_retries:
                        logger.warning("Periodic cleanup failed multiple times, will retry on next cycle")
                        retry_count = 0
                    else:
                        # Wait a bit before retrying
                        await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Fatal error in periodic cleanup loop: {e}", exc_info=True)
                # Wait before retrying the loop
                await asyncio.sleep(300)  # 5 minutes
