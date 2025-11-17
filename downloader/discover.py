from __future__ import annotations

from typing import Optional, List, Dict, Tuple
import re
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _extract_quality_info(source_tag) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Extract quality information from a source tag.
    
    Returns:
        Tuple of (width, height, quality_label) or (None, None, None) if not found
    """
    width = None
    height = None
    quality_label = None
    
    # Check for data attributes
    if source_tag:
        # Check for resolution attributes
        width_attr = source_tag.get("data-width") or source_tag.get("width")
        height_attr = source_tag.get("data-height") or source_tag.get("height")
        
        if width_attr:
            try:
                width = int(width_attr)
            except (ValueError, TypeError):
                pass
        
        if height_attr:
            try:
                height = int(height_attr)
            except (ValueError, TypeError):
                pass
        
        # Check for quality label
        quality_label = (
            source_tag.get("data-quality") or 
            source_tag.get("data-label") or 
            source_tag.get("label") or
            source_tag.get("title")
        )
        
        # Try to extract resolution from quality label (e.g., "1080p", "720p")
        if quality_label and not width:
            resolution_match = re.search(r'(\d+)p', quality_label, re.IGNORECASE)
            if resolution_match:
                height = int(resolution_match.group(1))
                # Estimate width based on common aspect ratios (16:9)
                width = int(height * 16 / 9)
    
    return width, height, quality_label


def discover_media_url(html_text: str, prefer_highest_quality: bool = True, http_client=None, base_url: Optional[str] = None) -> Optional[str]:
    """
    Parse Motherless video page HTML to extract the source URL.
    
    If multiple sources are available and prefer_highest_quality is True,
    selects the highest quality version based on resolution or file size.
    
    Args:
        html_text: HTML content of the video page
        prefer_highest_quality: If True, select highest quality when multiple sources exist
        
    Returns:
        URL of the best quality video source, or None if not found
    """
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Find all source tags
    sources = soup.select("video source[src]")
    
    if not sources:
        # Fallback: look for data-src or similar on video element
        video = soup.select_one("video")
        if video:
            for attr in ("data-src", "data-video", "src"):
                val = video.get(attr)
                if isinstance(val, str) and val.strip():
                    logger.debug(f"Found video URL from video[{attr}]: {val.strip()}")
                    return val.strip()
        return None
    
    # If only one source, return it
    if len(sources) == 1:
        src = sources[0].get("src")
        if isinstance(src, str) and src.strip():
            logger.debug(f"Found single source: {src.strip()}")
            return src.strip()
        return None
    
    # Multiple sources found - select best quality
    logger.info(f"Found {len(sources)} video sources, selecting highest quality...")
    
    source_info: List[Dict[str, any]] = []
    
    for source in sources:
        src = source.get("src")
        if not isinstance(src, str) or not src.strip():
            continue
        
        width, height, quality_label = _extract_quality_info(source)
        
        source_info.append({
            "url": src.strip(),
            "width": width,
            "height": height,
            "quality_label": quality_label,
            "source_tag": source
        })
    
    if not source_info:
        return None
    
    # If prefer_highest_quality is False, return first source
    if not prefer_highest_quality:
        logger.debug(f"Not preferring highest quality, returning first source: {source_info[0]['url']}")
        return source_info[0]["url"]
    
    # If we have resolution info, sort by that
    # Otherwise, try to get file sizes via HEAD requests
    sources_with_resolution = [s for s in source_info if s["height"] is not None]
    sources_without_resolution = [s for s in source_info if s["height"] is None]
    
    if sources_with_resolution:
        # Sort by resolution (height first, then width)
        sources_with_resolution.sort(key=lambda x: (
            x["height"] if x["height"] else 0,
            x["width"] if x["width"] else 0
        ), reverse=True)
        best_source = sources_with_resolution[0]
    elif http_client and sources_without_resolution:
        # No resolution info - check file sizes via HEAD requests
        logger.debug("No resolution info available, checking file sizes...")
        for source in sources_without_resolution:
            try:
                # Resolve relative URLs if needed
                from urllib.parse import urljoin
                if base_url and not source["url"].startswith("http"):
                    full_url = urljoin(base_url, source["url"])
                else:
                    full_url = source["url"]
                
                # Try HEAD request to get file size
                head_resp = http_client.head(full_url, follow_redirects=True, timeout=5.0)
                content_length = head_resp.headers.get("Content-Length")
                if content_length:
                    try:
                        source["file_size"] = int(content_length)
                    except (ValueError, TypeError):
                        source["file_size"] = 0
                else:
                    source["file_size"] = 0
            except Exception as e:
                logger.debug(f"Failed to get file size for {source['url']}: {e}")
                source["file_size"] = 0
        
        # Sort by file size (larger = higher quality)
        sources_without_resolution.sort(key=lambda x: x.get("file_size", 0), reverse=True)
        best_source = sources_without_resolution[0]
    else:
        # Fallback: just use first source
        best_source = source_info[0]
    
    resolution_str = (
        f"{best_source['width']}x{best_source['height']}" 
        if best_source.get('width') and best_source.get('height') 
        else "unknown"
    )
    file_size_str = (
        f" ({best_source.get('file_size', 0):,} bytes)" 
        if best_source.get('file_size') 
        else ""
    )
    
    logger.info(
        f"Selected highest quality source: {best_source['url']} "
        f"(Resolution: {resolution_str}, "
        f"Label: {best_source['quality_label'] or 'none'}{file_size_str})"
    )
    
    return best_source["url"]


def discover_title(html_text: str) -> Optional[str]:
    """Extract the display title from a Motherless video page.

    Primary selector: div.media-meta h1; fallback to <title>.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    h1 = soup.select_one("div.media-meta h1")
    if h1 and h1.text.strip():
        return h1.text.strip()
    if soup.title and soup.title.text.strip():
        return soup.title.text.strip()
    return None
