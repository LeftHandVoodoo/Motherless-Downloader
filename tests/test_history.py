"""Tests for the download history database module."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from downloader.history import DownloadHistory


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_history.db"
        history = DownloadHistory(db_path=db_path)
        yield history


def test_init_database(temp_db):
    """Test that database is initialized correctly."""
    assert temp_db.db_path.exists()


def test_add_download(temp_db):
    """Test adding a download to history."""
    download_data = {
        "id": "test-123",
        "url": "https://motherless.com/test",
        "filename": "test.mp4",
        "dest_path": "/downloads/test.mp4",
        "status": "COMPLETED",
        "total_bytes": 1000000,
        "received_bytes": 1000000,
        "speed_bps": 500000.0,
        "connections": 4,
        "adaptive": True,
        "error_message": None,
        "created_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
    }
    
    result = temp_db.add_download(download_data)
    assert result is True
    
    # Verify it was added
    retrieved = temp_db.get_download("test-123")
    assert retrieved is not None
    assert retrieved["id"] == "test-123"
    assert retrieved["url"] == "https://motherless.com/test"
    assert retrieved["filename"] == "test.mp4"
    assert retrieved["status"] == "COMPLETED"


def test_add_duplicate_download(temp_db):
    """Test that adding a duplicate download returns False."""
    download_data = {
        "id": "test-dup",
        "url": "https://motherless.com/test",
        "filename": "test.mp4",
        "dest_path": "/downloads/test.mp4",
        "status": "COMPLETED",
        "total_bytes": 1000000,
        "received_bytes": 1000000,
    }
    
    # First add should succeed
    result1 = temp_db.add_download(download_data)
    assert result1 is True
    
    # Second add should fail
    result2 = temp_db.add_download(download_data)
    assert result2 is False


def test_update_download(temp_db):
    """Test updating a download in history."""
    # Add a download
    download_data = {
        "id": "test-update",
        "url": "https://motherless.com/test",
        "filename": "test.mp4",
        "dest_path": "/downloads/test.mp4",
        "status": "DOWNLOADING",
        "total_bytes": 1000000,
        "received_bytes": 500000,
    }
    temp_db.add_download(download_data)
    
    # Update it
    updates = {
        "status": "COMPLETED",
        "received_bytes": 1000000,
        "completed_at": datetime.utcnow().isoformat(),
    }
    result = temp_db.update_download("test-update", updates)
    assert result is True
    
    # Verify the update
    retrieved = temp_db.get_download("test-update")
    assert retrieved["status"] == "COMPLETED"
    assert retrieved["received_bytes"] == 1000000
    assert retrieved["completed_at"] is not None


def test_update_nonexistent_download(temp_db):
    """Test updating a download that doesn't exist."""
    result = temp_db.update_download("nonexistent", {"status": "COMPLETED"})
    assert result is False


def test_get_download(temp_db):
    """Test retrieving a specific download."""
    download_data = {
        "id": "test-get",
        "url": "https://motherless.com/test",
        "filename": "test.mp4",
        "dest_path": "/downloads/test.mp4",
        "status": "COMPLETED",
        "total_bytes": 1000000,
        "received_bytes": 1000000,
    }
    temp_db.add_download(download_data)
    
    retrieved = temp_db.get_download("test-get")
    assert retrieved is not None
    assert retrieved["id"] == "test-get"


def test_get_nonexistent_download(temp_db):
    """Test retrieving a download that doesn't exist."""
    retrieved = temp_db.get_download("nonexistent")
    assert retrieved is None


def test_get_all_downloads(temp_db):
    """Test retrieving all downloads with pagination."""
    # Add multiple downloads
    for i in range(5):
        download_data = {
            "id": f"test-{i}",
            "url": f"https://motherless.com/test{i}",
            "filename": f"test{i}.mp4",
            "dest_path": f"/downloads/test{i}.mp4",
            "status": "COMPLETED",
            "total_bytes": 1000000,
            "received_bytes": 1000000,
        }
        temp_db.add_download(download_data)
    
    # Get all
    all_downloads = temp_db.get_all_downloads(limit=10, offset=0)
    assert len(all_downloads) == 5
    
    # Test pagination
    page1 = temp_db.get_all_downloads(limit=2, offset=0)
    assert len(page1) == 2
    
    page2 = temp_db.get_all_downloads(limit=2, offset=2)
    assert len(page2) == 2


def test_get_all_downloads_with_status_filter(temp_db):
    """Test retrieving downloads filtered by status."""
    # Add downloads with different statuses
    for status in ["COMPLETED", "FAILED", "CANCELLED"]:
        download_data = {
            "id": f"test-{status}",
            "url": f"https://motherless.com/{status}",
            "filename": f"{status}.mp4",
            "dest_path": f"/downloads/{status}.mp4",
            "status": status,
            "total_bytes": 1000000,
            "received_bytes": 1000000 if status == "COMPLETED" else 500000,
        }
        temp_db.add_download(download_data)
    
    # Filter by COMPLETED
    completed = temp_db.get_all_downloads(status="COMPLETED")
    assert len(completed) == 1
    assert completed[0]["status"] == "COMPLETED"
    
    # Filter by FAILED
    failed = temp_db.get_all_downloads(status="FAILED")
    assert len(failed) == 1
    assert failed[0]["status"] == "FAILED"


def test_get_all_downloads_with_search(temp_db):
    """Test retrieving downloads with search filter."""
    # Add downloads
    download_data1 = {
        "id": "test-1",
        "url": "https://motherless.com/video123",
        "filename": "vacation.mp4",
        "dest_path": "/downloads/vacation.mp4",
        "status": "COMPLETED",
        "total_bytes": 1000000,
        "received_bytes": 1000000,
    }
    download_data2 = {
        "id": "test-2",
        "url": "https://motherless.com/video456",
        "filename": "birthday.mp4",
        "dest_path": "/downloads/birthday.mp4",
        "status": "COMPLETED",
        "total_bytes": 2000000,
        "received_bytes": 2000000,
    }
    temp_db.add_download(download_data1)
    temp_db.add_download(download_data2)
    
    # Search by filename
    results = temp_db.get_all_downloads(search="vacation")
    assert len(results) == 1
    assert results[0]["filename"] == "vacation.mp4"
    
    # Search by URL
    results = temp_db.get_all_downloads(search="video456")
    assert len(results) == 1
    assert results[0]["url"] == "https://motherless.com/video456"


def test_get_statistics(temp_db):
    """Test getting aggregate statistics."""
    # Add downloads with different statuses
    downloads = [
        {"id": "test-1", "status": "COMPLETED", "total_bytes": 1000000},
        {"id": "test-2", "status": "COMPLETED", "total_bytes": 2000000},
        {"id": "test-3", "status": "FAILED", "total_bytes": 500000},
        {"id": "test-4", "status": "CANCELLED", "total_bytes": 300000},
    ]
    
    for dl in downloads:
        download_data = {
            "id": dl["id"],
            "url": f"https://motherless.com/{dl['id']}",
            "filename": f"{dl['id']}.mp4",
            "dest_path": f"/downloads/{dl['id']}.mp4",
            "status": dl["status"],
            "total_bytes": dl["total_bytes"],
            "received_bytes": dl["total_bytes"] if dl["status"] == "COMPLETED" else 0,
        }
        temp_db.add_download(download_data)
    
    stats = temp_db.get_statistics()
    assert stats["total"] == 4
    assert stats["completed"] == 2
    assert stats["failed"] == 1
    assert stats["cancelled"] == 1
    assert stats["total_bytes"] == 3800000  # Sum of all
    assert stats["completed_bytes"] == 3000000  # Sum of completed only


def test_delete_download(temp_db):
    """Test deleting a download from history."""
    download_data = {
        "id": "test-delete",
        "url": "https://motherless.com/test",
        "filename": "test.mp4",
        "dest_path": "/downloads/test.mp4",
        "status": "COMPLETED",
        "total_bytes": 1000000,
        "received_bytes": 1000000,
    }
    temp_db.add_download(download_data)
    
    # Verify it exists
    assert temp_db.get_download("test-delete") is not None
    
    # Delete it
    result = temp_db.delete_download("test-delete")
    assert result is True
    
    # Verify it's gone
    assert temp_db.get_download("test-delete") is None


def test_delete_nonexistent_download(temp_db):
    """Test deleting a download that doesn't exist."""
    result = temp_db.delete_download("nonexistent")
    assert result is False


def test_clear_old_downloads(temp_db):
    """Test clearing old downloads."""
    # Add old and new downloads
    old_date = (datetime.utcnow() - timedelta(days=35)).isoformat()
    new_date = datetime.utcnow().isoformat()
    
    old_download = {
        "id": "old-1",
        "url": "https://motherless.com/old",
        "filename": "old.mp4",
        "dest_path": "/downloads/old.mp4",
        "status": "COMPLETED",
        "total_bytes": 1000000,
        "received_bytes": 1000000,
        "created_at": old_date,
    }
    
    new_download = {
        "id": "new-1",
        "url": "https://motherless.com/new",
        "filename": "new.mp4",
        "dest_path": "/downloads/new.mp4",
        "status": "COMPLETED",
        "total_bytes": 2000000,
        "received_bytes": 2000000,
        "created_at": new_date,
    }
    
    temp_db.add_download(old_download)
    temp_db.add_download(new_download)
    
    # Clear downloads older than 30 days
    removed_count = temp_db.clear_old_downloads(days=30)
    assert removed_count == 1
    
    # Verify old one is gone, new one remains
    assert temp_db.get_download("old-1") is None
    assert temp_db.get_download("new-1") is not None


def test_clear_old_downloads_with_status_filter(temp_db):
    """Test clearing old downloads with status filter."""
    old_date = (datetime.utcnow() - timedelta(days=35)).isoformat()
    
    # Add old downloads with different statuses
    for status in ["COMPLETED", "FAILED"]:
        download_data = {
            "id": f"old-{status}",
            "url": f"https://motherless.com/old-{status}",
            "filename": f"old-{status}.mp4",
            "dest_path": f"/downloads/old-{status}.mp4",
            "status": status,
            "total_bytes": 1000000,
            "received_bytes": 1000000 if status == "COMPLETED" else 500000,
            "created_at": old_date,
        }
        temp_db.add_download(download_data)
    
    # Clear only old COMPLETED downloads
    removed_count = temp_db.clear_old_downloads(days=30, status="COMPLETED")
    assert removed_count == 1
    
    # Verify COMPLETED is gone, FAILED remains
    assert temp_db.get_download("old-COMPLETED") is None
    assert temp_db.get_download("old-FAILED") is not None

