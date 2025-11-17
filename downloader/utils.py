from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse
import hashlib
import re
import re as _re

ALLOWED_HOST_SUFFIXES: Tuple[str, ...] = (
    ".motherless.com",
    ".cdn.motherless.com",
    ".motherlessmedia.com",
)
ALLOWED_HOSTS_EXACT: Tuple[str, ...] = (
    "motherless.com",
    "cdn.motherless.com",
    "motherlessmedia.com",
)


@dataclass(frozen=True)
class UrlValidationResult:
    is_valid: bool
    message: str


@dataclass(frozen=True)
class HeadValidationResult:
    is_valid: bool
    message: str
    total_bytes: Optional[int] = None
    content_type: Optional[str] = None
    accept_ranges_bytes: bool = False
    suggested_filename: Optional[str] = None


def is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme.lower() == "https"


def is_allowed_host(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return host in ALLOWED_HOSTS_EXACT or any(host.endswith(suffix) for suffix in ALLOWED_HOST_SUFFIXES)


def validate_url(url: str) -> UrlValidationResult:
    if not url:
        return UrlValidationResult(False, "URL is empty")
    if not is_https_url(url):
        return UrlValidationResult(False, "URL must use https")
    if not is_allowed_host(url):
        return UrlValidationResult(False, "Host must be motherless.com or official CDN")
    return UrlValidationResult(True, "OK")


_FILENAME_RE = re.compile(r"filename\*=UTF-8''(?P<f>[^;]+)|filename=(?P<f2>\"?([^\";]+)\"?)", re.IGNORECASE)


def extract_filename_from_content_disposition(header_value: Optional[str]) -> Optional[str]:
    if not header_value:
        return None
    match = _FILENAME_RE.search(header_value)
    if not match:
        return None
    filename = match.group('f') or match.group(3)
    if not filename:
        return None
    return filename.strip().strip('"')


def get_url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


_INVALID_CHARS = _re.compile(r"[\\/:*?\"<>|]+")


def sanitize_title_for_fs(title: str) -> str:
    title = title.strip()
    title = _INVALID_CHARS.sub(" ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def _parse_total_from_content_range(value: Optional[str]) -> Optional[int]:
    # Example: bytes 0-0/12345
    if not value:
        return None
    try:
        parts = value.split("/")
        if len(parts) != 2:
            return None
        total_str = parts[1].strip()
        if total_str == "*":
            return None
        return int(total_str)
    except Exception:
        return None


def perform_head_validation(
    status_code: int,
    headers: dict[str, str],
) -> HeadValidationResult:
    # This function is designed to be fed with mocked HEAD/GET headers in tests.
    if status_code not in (200, 206):
        return HeadValidationResult(False, f"Unexpected status {status_code}")

    normalized = {k.lower(): v for k, v in headers.items()}

    content_length_raw = normalized.get("content-length")
    total_bytes: Optional[int] = None
    if content_length_raw is not None:
        try:
            total_bytes = int(content_length_raw)
        except (TypeError, ValueError):
            return HeadValidationResult(False, "Content-Length invalid")
    else:
        # Fallback: derive from Content-Range if present (usually with 206 responses)
        total_bytes = _parse_total_from_content_range(normalized.get("content-range"))
        if total_bytes is None:
            return HeadValidationResult(False, "Content-Length missing")

    content_type = normalized.get("content-type", "").lower()
    if not (content_type.startswith("video/") or content_type.startswith("application/octet-stream")):
        return HeadValidationResult(False, "Unsupported Content-Type")

    accept_ranges = normalized.get("accept-ranges", "").lower()
    accept_ranges_bytes = "bytes" in accept_ranges or status_code == 206

    suggested_filename = extract_filename_from_content_disposition(normalized.get("content-disposition"))

    return HeadValidationResult(
        True,
        "OK",
        total_bytes=total_bytes,
        content_type=content_type,
        accept_ranges_bytes=accept_ranges_bytes,
        suggested_filename=suggested_filename,
    )
