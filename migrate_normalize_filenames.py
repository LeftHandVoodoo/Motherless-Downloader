#!/usr/bin/env python3
"""
Migration script to normalize existing filenames in the download history database.

This script:
1. Reads all downloads from the history database
2. Normalizes their filenames using the normalize_filename function
3. Updates the database with normalized filenames
4. Optionally renames actual files on disk if they exist

Usage:
    python migrate_normalize_filenames.py [--dry-run] [--rename-files]
    
    --dry-run: Show what would be changed without actually updating the database
    --rename-files: Also rename actual files on disk (default: only update database)
"""

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict, Tuple

from downloader.history import DownloadHistory
from downloader.utils import normalize_filename


def get_all_downloads(db_path: Path) -> List[Dict]:
    """Get all downloads from the database."""
    downloads = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, filename, dest_path, url_filename, status
                FROM downloads
                ORDER BY created_at DESC
            """)
            for row in cursor:
                downloads.append({
                    'id': row['id'],
                    'filename': row['filename'],
                    'dest_path': row['dest_path'],
                    'url_filename': row['url_filename'],
                    'status': row['status']
                })
    except Exception as e:
        print(f"Error reading database: {e}", file=sys.stderr)
        sys.exit(1)
    
    return downloads


def normalize_history_entry(entry: Dict, rename_files: bool = False) -> Tuple[Dict, bool]:
    """
    Normalize a history entry's filename.
    
    Returns:
        (updated_entry, changed) tuple where changed indicates if any updates were made
    """
    updated = entry.copy()
    changed = False
    
    # Normalize the filename field
    if entry['filename']:
        normalized = normalize_filename(entry['filename'])
        if normalized != entry['filename']:
            updated['filename'] = normalized
            changed = True
    
    # Normalize the dest_path filename if dest_path exists
    if entry['dest_path']:
        dest_path = Path(entry['dest_path'])
        if dest_path.exists() or dest_path.parent.exists():
            # Extract just the filename part
            original_name = dest_path.name
            normalized_name = normalize_filename(original_name)
            
            if normalized_name != original_name:
                new_path = dest_path.parent / normalized_name
                updated['dest_path'] = str(new_path)
                changed = True
                
                # Optionally rename the actual file
                if rename_files and dest_path.exists():
                    try:
                        dest_path.rename(new_path)
                        print(f"  [OK] Renamed file: {original_name} -> {normalized_name}")
                    except Exception as e:
                        print(f"  [ERROR] Failed to rename file {dest_path}: {e}", file=sys.stderr)
                        # Revert dest_path change if rename failed
                        updated['dest_path'] = entry['dest_path']
    
    return updated, changed


def update_download_in_db(db_path: Path, download_id: str, updates: Dict) -> bool:
    """Update a download entry in the database."""
    try:
        with sqlite3.connect(db_path) as conn:
            # Build update query dynamically based on what changed
            fields = []
            values = []
            
            if 'filename' in updates:
                fields.append('filename = ?')
                values.append(updates['filename'])
            
            if 'dest_path' in updates:
                fields.append('dest_path = ?')
                values.append(updates['dest_path'])
                # Also update file_exists status
                file_exists = 1 if Path(updates['dest_path']).exists() else 0
                fields.append('file_exists = ?')
                values.append(file_exists)
            
            if not fields:
                return False
            
            # Add updated_at timestamp
            from datetime import datetime, timezone
            fields.append('updated_at = ?')
            values.append(datetime.now(timezone.utc).isoformat())
            
            # Add id for WHERE clause
            values.append(download_id)
            
            query = f"""
                UPDATE downloads
                SET {', '.join(fields)}
                WHERE id = ?
            """
            
            conn.execute(query, values)
            conn.commit()
            return True
    except Exception as e:
        print(f"  ✗ Database update failed: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Normalize filenames in download history database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without actually updating'
    )
    parser.add_argument(
        '--rename-files',
        action='store_true',
        help='Also rename actual files on disk (default: only update database)'
    )
    args = parser.parse_args()
    
    # Initialize DownloadHistory to get the database path
    history = DownloadHistory()
    db_path = Path(history.db_path)
    
    if not db_path.exists():
        print(f"Database not found at: {db_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reading downloads from: {db_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'UPDATE'} {'+ RENAME FILES' if args.rename_files else ''}")
    print("=" * 80)
    
    # Get all downloads
    downloads = get_all_downloads(db_path)
    print(f"Found {len(downloads)} downloads in history\n")
    
    if not downloads:
        print("No downloads to process.")
        return
    
    # Process each download
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for entry in downloads:
        download_id = entry['id']
        original_filename = entry['filename'] or entry['url_filename'] or 'N/A'
        
        # Normalize the entry
        updated_entry, changed = normalize_history_entry(entry, rename_files=args.rename_files)
        
        if not changed:
            skipped_count += 1
            continue
        
        # Show what would change
        print(f"Download ID: {download_id[:8]}...")
        if entry['filename'] != updated_entry.get('filename', entry['filename']):
            print(f"  Filename: {entry['filename']} -> {updated_entry['filename']}")
        if entry['dest_path'] != updated_entry.get('dest_path', entry['dest_path']):
            print(f"  Path: {Path(entry['dest_path']).name} -> {Path(updated_entry['dest_path']).name}")
        
        # Update database if not dry run
        if not args.dry_run:
            if update_download_in_db(db_path, download_id, updated_entry):
                updated_count += 1
                print(f"  [OK] Updated in database")
            else:
                error_count += 1
                print(f"  [ERROR] Failed to update database")
        else:
            updated_count += 1
            print(f"  [DRY RUN] Would update")
        
        print()
    
    # Summary
    print("=" * 80)
    print(f"Summary:")
    print(f"  Total downloads: {len(downloads)}")
    print(f"  {'Would update' if args.dry_run else 'Updated'}: {updated_count}")
    print(f"  Skipped (no changes): {skipped_count}")
    if error_count > 0:
        print(f"  Errors: {error_count}")
    
    if args.dry_run:
        print("\nRun without --dry-run to apply changes.")


if __name__ == '__main__':
    main()

