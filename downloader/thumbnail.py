"""Thumbnail extraction utilities for video files."""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Ensure logger is configured
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Add console handler if not already configured
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def extract_thumbnail(
    video_path: Path,
    thumbnail_dir: Optional[Path] = None,
    timestamp: str = "00:00:01"
) -> Optional[Path]:
    """
    Extract a thumbnail from a video file using ffmpeg.
    
    Args:
        video_path: Path to the video file
        thumbnail_dir: Directory to save thumbnail (defaults to same directory as video)
        timestamp: Timestamp to extract frame from (default: 1 second)
        
    Returns:
        Path to the thumbnail image, or None if extraction failed
    """
    if not video_path.exists():
        logger.warning(f"Video file does not exist: {video_path}")
        return None
    
    # Check if file is a video by extension
    video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v'}
    file_ext = video_path.suffix.lower()
    
    # Allow .bin files (common when filename detection fails) - try extraction anyway
    # ffmpeg will fail gracefully if it's not a video
    if file_ext not in video_extensions and file_ext != '.bin':
        logger.debug(f"File is not a video (extension: {file_ext}): {video_path}")
        return None
    
    if file_ext == '.bin':
        logger.info(f"Attempting thumbnail extraction for .bin file (may be a video): {video_path}")
    else:
        logger.info(f"Attempting thumbnail extraction for video: {video_path} (extension: {file_ext})")
    
    # Determine thumbnail path
    if thumbnail_dir is None:
        thumbnail_dir = video_path.parent
    
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_path = thumbnail_dir / f"{video_path.stem}_thumb.jpg"
    
    # Check if ffmpeg is available
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=5
        )
        logger.debug("ffmpeg found and accessible")
    except FileNotFoundError:
        logger.warning("ffmpeg not found in PATH. Thumbnail extraction skipped.")
        return None
    except subprocess.CalledProcessError as e:
        logger.warning(f"ffmpeg version check failed: {e}")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg version check timed out")
        return None
    
    # Extract thumbnail using ffmpeg
    # Use -ss before -i for faster seeking, and -frames:v instead of -vframes for newer ffmpeg
    try:
        logger.info(f"Running ffmpeg to extract thumbnail from {video_path} -> {thumbnail_path}")
        
        # Convert paths to strings for Windows compatibility
        video_path_str = str(video_path.resolve())
        thumbnail_path_str = str(thumbnail_path.resolve())
        
        cmd = [
            "ffmpeg",
            "-ss", timestamp,  # Seek before input for faster processing
            "-i", video_path_str,
            "-frames:v", "1",  # Extract 1 video frame (more compatible than -vframes)
            "-vf", "scale=320:-1",  # Scale to 320px width, maintain aspect ratio
            "-q:v", "2",  # High quality (lower is better, 2 is very high)
            "-y",  # Overwrite if exists
            thumbnail_path_str
        ]
        
        logger.debug(f"ffmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            timeout=30,
            text=False  # Keep as bytes for decoding
        )
        
        # Check if file was created
        if thumbnail_path.exists() and thumbnail_path.stat().st_size > 0:
            logger.info(f"Successfully extracted thumbnail ({thumbnail_path.stat().st_size} bytes): {thumbnail_path}")
            return thumbnail_path
        else:
            logger.warning(f"ffmpeg completed but thumbnail file not found or empty: {thumbnail_path}")
            if result.stderr:
                stderr_text = result.stderr.decode('utf-8', errors='ignore')
                logger.warning(f"ffmpeg stderr: {stderr_text}")
            if result.stdout:
                stdout_text = result.stdout.decode('utf-8', errors='ignore')
                logger.debug(f"ffmpeg stdout: {stdout_text}")
            return None
            
    except subprocess.CalledProcessError as e:
        error_msg = ""
        if e.stderr:
            error_msg = e.stderr.decode('utf-8', errors='ignore')
        elif e.stdout:
            error_msg = e.stdout.decode('utf-8', errors='ignore')
        else:
            error_msg = str(e)
        
        logger.error(f"ffmpeg failed to extract thumbnail (exit code {e.returncode}): {error_msg}")
        
        # Log full output for debugging
        if e.stderr:
            logger.debug(f"Full stderr: {e.stderr.decode('utf-8', errors='ignore')}")
        if e.stdout:
            logger.debug(f"Full stdout: {e.stdout.decode('utf-8', errors='ignore')}")
        
        return None
    except subprocess.TimeoutExpired:
        logger.error("Thumbnail extraction timed out after 30 seconds")
        return None
    except Exception as e:
        logger.error(f"Unexpected error extracting thumbnail: {e}", exc_info=True)
        return None

