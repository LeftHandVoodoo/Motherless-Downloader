#!/usr/bin/env python3
"""Extract thumbnails for video files that don't have them yet."""
import sys
from pathlib import Path
import sqlite3
from platformdirs import user_data_dir
from downloader.thumbnail import extract_thumbnail
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def extract_missing_thumbnails():
    """Extract thumbnails for completed downloads that don't have them."""
    data_dir = Path(user_data_dir("MotherlessDownloader", "LeftHandVoodoo"))
    db_path = data_dir / "history.db"
    
    if not db_path.exists():
        print(f"[ERROR] History database not found at: {db_path}")
        return
    
    print(f"[INFO] Checking history database: {db_path}")
    print("=" * 80)
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Get completed downloads without thumbnails (check both COMPLETED and completed)
        cursor = conn.execute("""
            SELECT id, filename, dest_path, status
            FROM downloads
            WHERE status IN ('COMPLETED', 'completed')
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        print(f"Found {len(rows)} completed downloads\n")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for row in rows:
            download_id = row['id']
            dest_path = row['dest_path']
            
            # Check if thumbnail_path column exists and is empty
            cursor_check = conn.execute("""
                SELECT thumbnail_path FROM downloads WHERE id = ?
            """, (download_id,))
            check_row = cursor_check.fetchone()
            
            # Check if thumbnail already exists
            has_thumbnail = False
            if check_row:
                try:
                    if 'thumbnail_path' in check_row.keys() and check_row['thumbnail_path']:
                        thumb_path = Path(check_row['thumbnail_path'])
                        if thumb_path.exists():
                            has_thumbnail = True
                except (KeyError, AttributeError):
                    pass
            
            if has_thumbnail:
                skipped_count += 1
                continue
            
            if not dest_path:
                print(f"[SKIP] {download_id}: No dest_path")
                skipped_count += 1
                continue
            
            video_path = Path(dest_path)
            if not video_path.exists():
                print(f"[SKIP] {download_id}: File not found: {video_path}")
                skipped_count += 1
                continue
            
            # Check if it's a video file
            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.bin'}
            if video_path.suffix.lower() not in video_extensions:
                print(f"[SKIP] {download_id}: Not a video file ({video_path.suffix})")
                skipped_count += 1
                continue
            
            print(f"[PROCESSING] {download_id}")
            print(f"  File: {video_path.name}")
            print(f"  Extension: {video_path.suffix}")
            
            try:
                thumb = extract_thumbnail(video_path)
                if thumb:
                    # Update database
                    conn.execute(
                        "UPDATE downloads SET thumbnail_path = ? WHERE id = ?",
                        (str(thumb), download_id)
                    )
                    conn.commit()
                    print(f"  [SUCCESS] Thumbnail: {thumb.name}")
                    updated_count += 1
                else:
                    print(f"  [FAILED] Thumbnail extraction returned None")
                    error_count += 1
            except Exception as e:
                print(f"  [ERROR] {e}")
                error_count += 1
            
            print()
        
        print("=" * 80)
        print(f"Summary:")
        print(f"  Updated: {updated_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")


if __name__ == "__main__":
    extract_missing_thumbnails()

