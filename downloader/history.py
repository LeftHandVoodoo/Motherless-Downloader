"""Download history database management using SQLite."""
from __future__ import annotations

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from platformdirs import user_data_dir

logger = logging.getLogger(__name__)


class DownloadHistory:
    """Manages persistent download history using SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the download history database.
        
        Args:
            db_path: Path to SQLite database file. If None, uses platform-appropriate data directory.
        """
        if db_path is None:
            data_dir = Path(user_data_dir("MotherlessDownloader", "LeftHandVoodoo"))
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "history.db"
        
        self.db_path = db_path
        self._init_database()
        logger.info(f"Initialized download history database at {self.db_path}")

    def _init_database(self):
        """Create the database schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    filename TEXT,
                    url_filename TEXT,
                    dest_path TEXT,
                    status TEXT NOT NULL,
                    total_bytes INTEGER DEFAULT 0,
                    received_bytes INTEGER DEFAULT 0,
                    speed_bps REAL DEFAULT 0.0,
                    connections INTEGER DEFAULT 4,
                    adaptive INTEGER DEFAULT 1,
                    error_message TEXT,
                    thumbnail_path TEXT,
                    file_exists INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Add new columns if they don't exist (for existing databases)
            new_columns = [
                ("thumbnail_path", "TEXT"),
                ("url_filename", "TEXT"),
                ("file_exists", "INTEGER DEFAULT 0"),
            ]
            
            for column_name, column_type in new_columns:
                try:
                    conn.execute(f"ALTER TABLE downloads ADD COLUMN {column_name} {column_type}")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            
            # Create indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON downloads(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON downloads(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON downloads(url)")
            conn.commit()
            logger.debug("Database schema initialized")

    def add_download(self, download_data: Dict[str, Any]) -> bool:
        """
        Add a new download to history.
        
        Args:
            download_data: Dictionary containing download information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.utcnow().isoformat()
                # Extract filename from URL if not provided
                url_filename = download_data.get("url_filename")
                if not url_filename:
                    from urllib.parse import urlparse
                    parsed = urlparse(download_data.get("url", ""))
                    url_filename = Path(parsed.path).name if parsed.path else None
                
                # Check if file exists
                dest_path = download_data.get("dest_path")
                file_exists = 0
                if dest_path:
                    file_exists = 1 if Path(dest_path).exists() else 0
                
                conn.execute("""
                    INSERT INTO downloads (
                        id, url, filename, url_filename, dest_path, status, total_bytes, received_bytes,
                        speed_bps, connections, adaptive, error_message, thumbnail_path, file_exists,
                        created_at, completed_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    download_data.get("id"),
                    download_data.get("url"),
                    download_data.get("filename"),
                    url_filename,
                    dest_path,
                    download_data.get("status"),
                    download_data.get("total_bytes", 0),
                    download_data.get("received_bytes", 0),
                    download_data.get("speed_bps", 0.0),
                    download_data.get("connections", 4),
                    1 if download_data.get("adaptive", True) else 0,
                    download_data.get("error_message"),
                    download_data.get("thumbnail_path"),
                    file_exists,
                    download_data.get("created_at", now),
                    download_data.get("completed_at"),
                    now
                ))
                conn.commit()
                logger.debug(f"Added download to history: {download_data.get('id')}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Download already exists in history: {download_data.get('id')}")
            return False
        except Exception as e:
            logger.error(f"Failed to add download to history: {e}")
            return False

    def update_download(self, download_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing download in history.
        
        Args:
            download_id: The download ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build dynamic UPDATE query based on provided fields
            update_fields = []
            values = []
            
            # Check file existence if dest_path is being updated
            if "dest_path" in updates:
                dest_path = updates["dest_path"]
                file_exists = 1 if dest_path and Path(dest_path).exists() else 0
                updates["file_exists"] = file_exists
            
            for field in ["status", "total_bytes", "received_bytes", "speed_bps", 
                         "filename", "url_filename", "dest_path", "error_message", 
                         "completed_at", "thumbnail_path", "file_exists"]:
                if field in updates:
                    update_fields.append(f"{field} = ?")
                    values.append(updates[field])
            
            # Always check file existence on update if dest_path exists
            if "dest_path" not in updates:
                # Re-check existing dest_path
                existing = self.get_download(download_id)
                if existing and existing.get("dest_path"):
                    file_exists = 1 if Path(existing["dest_path"]).exists() else 0
                    update_fields.append("file_exists = ?")
                    values.append(file_exists)
            
            if not update_fields:
                return True  # Nothing to update
            
            # Always update the updated_at timestamp
            update_fields.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(download_id)
            
            query = f"UPDATE downloads SET {', '.join(update_fields)} WHERE id = ?"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"Updated download in history: {download_id}")
                    return True
                else:
                    logger.warning(f"Download not found in history: {download_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update download in history: {e}")
            return False

    def get_download(self, download_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single download by ID.
        
        Args:
            download_id: The download ID
            
        Returns:
            Dictionary with download data or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM downloads WHERE id = ?",
                    (download_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve download from history: {e}")
            return None

    def get_all_downloads(
        self,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve downloads with optional filtering.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            status: Filter by status (QUEUED, DOWNLOADING, COMPLETED, etc.)
            search: Search term for URL or filename
            
        Returns:
            List of download dictionaries
        """
        try:
            query = "SELECT * FROM downloads WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if search:
                query += " AND (url LIKE ? OR filename LIKE ?)"
                search_term = f"%{search}%"
                params.extend([search_term, search_term])
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to retrieve downloads from history: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics about download history.
        
        Returns:
            Dictionary with statistics (total downloads, completed, failed, total bytes, etc.)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) as cancelled,
                        SUM(total_bytes) as total_bytes,
                        SUM(CASE WHEN status = 'COMPLETED' THEN total_bytes ELSE 0 END) as completed_bytes
                    FROM downloads
                """)
                row = cursor.fetchone()
                
                return {
                    "total": row[0] or 0,
                    "completed": row[1] or 0,
                    "failed": row[2] or 0,
                    "cancelled": row[3] or 0,
                    "total_bytes": row[4] or 0,
                    "completed_bytes": row[5] or 0
                }
                
        except Exception as e:
            logger.error(f"Failed to retrieve statistics: {e}")
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "cancelled": 0,
                "total_bytes": 0,
                "completed_bytes": 0
            }

    def delete_download(self, download_id: str) -> bool:
        """
        Delete a download from history.
        
        Args:
            download_id: The download ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"Deleted download from history: {download_id}")
                    return True
                else:
                    logger.warning(f"Download not found in history: {download_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete download from history: {e}")
            return False

    def clear_old_downloads(self, days: int = 30, status: Optional[str] = None) -> int:
        """
        Clear downloads older than specified days.
        
        Args:
            days: Number of days to keep
            status: Optional status filter (e.g., only delete COMPLETED)
            
        Returns:
            Number of downloads deleted
        """
        try:
            cutoff_date = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            # Subtract days
            import datetime as dt
            cutoff_date = cutoff_date - dt.timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            query = "DELETE FROM downloads WHERE created_at < ?"
            params = [cutoff_str]
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                deleted_count = cursor.rowcount
                
                logger.info(f"Cleared {deleted_count} old downloads from history")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to clear old downloads: {e}")
            return 0

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a SQLite row to a dictionary."""
        # sqlite3.Row doesn't support .get(), so we need to check keys differently
        thumbnail_path = None
        url_filename = None
        file_exists = 0
        
        try:
            # Try to access optional columns if they exist
            if "thumbnail_path" in row.keys():
                thumbnail_path = row["thumbnail_path"]
            if "url_filename" in row.keys():
                url_filename = row["url_filename"]
            if "file_exists" in row.keys():
                file_exists = row["file_exists"]
        except (KeyError, AttributeError):
            pass
        
        # Re-check file existence if dest_path exists
        dest_path = row["dest_path"]
        if dest_path:
            file_exists = 1 if Path(dest_path).exists() else 0
        
        return {
            "id": row["id"],
            "url": row["url"],
            "filename": row["filename"],
            "url_filename": url_filename,
            "dest_path": dest_path,
            "status": row["status"],
            "total_bytes": row["total_bytes"],
            "received_bytes": row["received_bytes"],
            "speed_bps": row["speed_bps"],
            "connections": row["connections"],
            "adaptive": bool(row["adaptive"]),
            "error_message": row["error_message"],
            "thumbnail_path": thumbnail_path,
            "file_exists": bool(file_exists),
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
            "updated_at": row["updated_at"]
        }

