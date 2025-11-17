#!/usr/bin/env python3
"""Script to check thumbnail extraction status and test thumbnail creation."""
import sys
from pathlib import Path
import sqlite3
from platformdirs import user_data_dir
from downloader.thumbnail import extract_thumbnail
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def check_history_db():
    """Check the history database for downloads and thumbnail status."""
    data_dir = Path(user_data_dir("MotherlessDownloader", "LeftHandVoodoo"))
    db_path = data_dir / "history.db"
    
    if not db_path.exists():
        print(f"[ERROR] History database not found at: {db_path}")
        return
    
    print(f"[INFO] Checking history database: {db_path}")
    print("=" * 80)
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        # First check all downloads
        cursor = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM downloads
            GROUP BY status
        """)
        status_counts = cursor.fetchall()
        print(f"\nDownload status breakdown:")
        for row in status_counts:
            print(f"  {row['status']}: {row['count']}")
        print()
        
        # Then get recent downloads regardless of status
        cursor = conn.execute("""
            SELECT id, filename, dest_path, status, thumbnail_path, completed_at, created_at
            FROM downloads
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("No completed downloads found in history.")
            return
        
        print(f"\nFound {len(rows)} completed downloads:\n")
        
        for row in rows:
            print(f"ID: {row['id']}")
            print(f"  Filename: {row['filename']}")
            print(f"  Path: {row['dest_path']}")
            print(f"  Status: {row['status']}")
            # Check if thumbnail_path column exists
            thumb_path_val = None
            try:
                if 'thumbnail_path' in row.keys():
                    thumb_path_val = row['thumbnail_path']
            except (KeyError, AttributeError):
                pass
            
            thumb_status = thumb_path_val or '[NOT SET]'
            print(f"  Thumbnail: {thumb_status}")
            
            # Check if files exist
            if row['dest_path']:
                video_path = Path(row['dest_path'])
                if video_path.exists():
                    print(f"  Video exists: YES ({video_path.stat().st_size:,} bytes)")
                    print(f"  Extension: {video_path.suffix}")
                    
                    # Check if thumbnail exists
                    if thumb_path_val:
                        thumb_path = Path(row['thumbnail_path'])
                        if thumb_path.exists():
                            print(f"  Thumbnail exists: YES ({thumb_path.stat().st_size:,} bytes)")
                        else:
                            print(f"  Thumbnail missing: NO (path: {thumb_path})")
                    else:
                        print(f"  Thumbnail not extracted: NO")
                        # Try to extract now
                        print(f"  Attempting extraction now...")
                        thumb = extract_thumbnail(video_path)
                        if thumb:
                            print(f"  [SUCCESS] Extracted: {thumb}")
                            # Update database
                            conn.execute(
                                "UPDATE downloads SET thumbnail_path = ? WHERE id = ?",
                                (str(thumb), row['id'])
                            )
                            conn.commit()
                            print(f"  [SUCCESS] Updated database")
                        else:
                            print(f"  [FAILED] Extraction failed (check logs above)")
                else:
                    print(f"  Video missing: NO (path: {video_path})")
            
            print()


def test_thumbnail_extraction(video_path: str):
    """Test thumbnail extraction on a specific file."""
    path = Path(video_path)
    
    if not path.exists():
        print(f"[ERROR] File not found: {path}")
        return
    
    print(f"[TEST] Testing thumbnail extraction for: {path}")
    print(f"       Extension: {path.suffix}")
    print(f"       Size: {path.stat().st_size:,} bytes")
    print()
    
    result = extract_thumbnail(path)
    
    if result:
        print(f"[SUCCESS] Thumbnail created: {result}")
        print(f"         Size: {result.stat().st_size:,} bytes")
    else:
        print(f"[FAILED] Failed to extract thumbnail (check logs above for details)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific file
        test_thumbnail_extraction(sys.argv[1])
    else:
        # Check history database
        check_history_db()
        print("\n" + "=" * 80)
        print("[TIP] Run with a file path to test thumbnail extraction:")
        print("      python check_thumbnails.py \"C:/path/to/video.mp4\"")

