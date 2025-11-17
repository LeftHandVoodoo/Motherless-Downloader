from __future__ import annotations

from typing import Optional
import re

from bs4 import BeautifulSoup


def discover_media_url(html_text: str) -> Optional[str]:
    """Parse Motherless video page HTML to extract the source URL.

    Looks for <video> <source src="..."> or data attributes.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    # Try video > source
    source = soup.select_one("video source[src]")
    if source and source.get("src"):
        return source.get("src")
    # Fallback: look for data-src or similar
    video = soup.select_one("video")
    if video:
        for attr in ("data-src", "data-video", "src"):
            val = video.get(attr)
            if val:
                return val
    return None


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
