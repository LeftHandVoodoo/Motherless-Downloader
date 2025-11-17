from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
import hashlib
import re

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


def is_valid_url(url: str) -> bool:
    """Simple boolean wrapper for validate_url."""
    return validate_url(url).is_valid


_FILENAME_RE = re.compile(r"filename\*=UTF-8''(?P<utf8>[^;]+)|filename=\"?(?P<regular>[^\";]+)\"?", re.IGNORECASE)


def extract_filename_from_content_disposition(header_value: Optional[str]) -> Optional[str]:
    if not header_value:
        return None
    match = _FILENAME_RE.search(header_value)
    if not match:
        return None
    filename = match.group('utf8') or match.group('regular')
    if not filename:
        return None
    return filename.strip().strip('"')


def get_url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


_INVALID_CHARS = re.compile(r"[\\/:*?\"<>|]+")


def sanitize_title_for_fs(title: str) -> str:
    title = title.strip()
    title = _INVALID_CHARS.sub(" ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def normalize_filename(filename: str) -> str:
    """
    Normalize a filename by:
    - Removing random number strings and trailing IDs (e.g., "_5377767", "video123" -> "video")
    - Preserving quality indicators (720p, 1080p, 4K, etc.)
    - Preserving parentheses content (especially years like "(1985)")
    - Preserving meaningful numbers (single/double digits in context)
    - Capitalizing appropriately (title case)
    - Normalizing spacing
    - Preserving file extension
    
    Args:
        filename: The filename to normalize (may include extension)
        
    Returns:
        Normalized filename with proper capitalization and cleaned of random numbers
    """
    if not filename:
        return filename
    
    # Split into name and extension
    path_obj = Path(filename)
    stem = path_obj.stem
    ext = path_obj.suffix
    
    # Step 1: Remove trailing underscore + number/alphanumeric patterns (e.g., "_5377767", "_xhaSMU3")
    # Pattern: underscore followed by alphanumeric sequence (typically 6+ chars, or 3+ digits)
    stem = re.sub(r'_[\da-zA-Z]{6,}$', '', stem)  # Remove trailing _1234567 or _abc123def
    stem = re.sub(r'_\d{3,}$', '', stem)  # Also catch shorter numeric IDs like _585662
    stem = re.sub(r'_[a-z]+[A-Z0-9]+[a-z]*$', '', stem)  # Remove trailing mixed case codes like _xhaSMU3
    
    # Step 2: Preserve quality indicators and part numbers before processing
    # Extract quality indicators (720p, 1080p, 4K, etc.) and part numbers
    quality_patterns = []
    part_patterns = []
    
    # Quality indicators: numbers followed by p, or 4K/8K (with optional underscore or hyphen prefix)
    # Also capture the prefix to preserve it
    quality_matches = list(re.finditer(r'([-_]?)(\d+p|4K|8K|HD|SD)', stem, re.IGNORECASE))
    for match in reversed(quality_matches):  # Process in reverse to preserve indices
        prefix = match.group(1)
        quality = match.group(2)
        # Preserve original case for 4K/8K
        if quality.upper() in ('4K', '8K'):
            quality = quality.upper()
        full_pattern = prefix + quality
        quality_patterns.append((match.start(), match.end(), full_pattern))
        stem = stem[:match.start()] + ' ' + stem[match.end():]
    
    # Part numbers: "Part 1", "Part 2", etc.
    part_matches = list(re.finditer(r'[-_]?(Part\s+\d+)', stem, re.IGNORECASE))
    for match in reversed(part_matches):
        part_patterns.append((match.start(), match.end(), match.group()))
        stem = stem[:match.start()] + ' ' + stem[match.end():]
    
    # Step 3: Preserve parentheses content (especially years)
    # Extract parentheses with content
    paren_patterns = []
    paren_matches = list(re.finditer(r'\(([^)]+)\)', stem))
    for match in reversed(paren_matches):
        content = match.group(1)
        # If it looks like a year (4 digits) or other meaningful content, preserve it
        if re.match(r'^\d{4}$', content.strip()) or len(content.strip()) > 0:
            paren_patterns.append((match.start(), match.end(), match.group()))
            stem = stem[:match.start()] + ' ' + stem[match.end():]
    
    # Step 4: Remove embedded alphanumeric codes (like "8A2CD52", "xhaSMU3")
    # But be careful - don't remove if it's the only content, if it's before quality indicators, or if it's a word
    # Pattern: sequences that are clearly IDs (mixed case with numbers, or all caps with numbers)
    
    # Check if there's a quality indicator - if so, preserve alphanumeric codes before it
    has_quality = bool(quality_patterns)
    
    # If there's a quality indicator, we need to be more careful about removing codes
    # that might be part of the filename (like "8A2CD52-720p")
    if has_quality:
        # Don't remove codes if they're the main content before quality indicator
        # Just remove trailing mixed case codes
        stem = re.sub(r'\b[a-z]{2,}[A-Z0-9]{2,}[a-z]*\b', '', stem)
    else:
        # Remove mixed case codes like "xhaSMU3" (lowercase + uppercase + number)
        stem = re.sub(r'\b[a-z]{2,}[A-Z0-9]{2,}[a-z]*\b', '', stem)
        
        # Remove uppercase alphanumeric codes that are clearly IDs
        # Pattern: 4+ uppercase letters/numbers that contain at least one number
        # But preserve if they're common words
        # Don't remove if it would leave nothing
        original_stem = stem
        # Only remove if it contains numbers (likely an ID)
        stem = re.sub(r'\b[A-Z0-9]*\d+[A-Z0-9]*\b', '', stem)
        # If removal left us with nothing meaningful, don't remove
        if not stem.strip() or len([w for w in stem.strip().split() if w]) == 0:
            stem = original_stem
    
    # Step 5: Handle numbers more carefully
    # Remove long number sequences (3+ digits) but preserve single/double digits
    # Also handle cases like "video123" -> "video" (numbers attached to words)
    
    # First, handle numbers attached directly to words (like "video123")
    # Split word-number combinations
    stem = re.sub(r'([a-zA-Z]+)(\d{3,})', r'\1', stem)  # Remove 3+ digits attached to words
    
    # Remove standalone 3+ digit sequences (these are likely random IDs)
    stem = re.sub(r'\b\d{3,}\b', '', stem)
    
    # Step 6: Handle numbers more intelligently
    # Remove 3-digit numbers that are clearly IDs (standalone, not part of years/quality)
    # But preserve single/double digits and meaningful numbers
    
    # First, normalize separators to make pattern matching easier
    stem = re.sub(r'[\s\-_]+', ' ', stem)
    stem = stem.strip()
    
    # Remove standalone 3-digit numbers (these are likely IDs, not meaningful)
    # But be careful - don't remove if they're part of a larger pattern
    stem = re.sub(r'\b\d{3}\b', '', stem)
    
    # Now handle remaining numbers: split by digits to separate words
    # But preserve single/double digits by using a different approach
    # Split the stem into parts, preserving single/double digits
    parts = []
    current_part = []
    i = 0
    
    while i < len(stem):
        if stem[i].isdigit():
            # Collect digits
            num_start = i
            while i < len(stem) and stem[i].isdigit():
                i += 1
            num_str = stem[num_start:i]
            # If it's 1-2 digits, preserve it; otherwise skip (already removed)
            if len(num_str) <= 2:
                if current_part:
                    parts.append(''.join(current_part))
                    current_part = []
                parts.append(num_str)
            # Skip longer numbers (already removed, but handle edge cases)
            continue
        elif stem[i].isspace():
            if current_part:
                parts.append(''.join(current_part))
                current_part = []
            i += 1
        else:
            current_part.append(stem[i])
            i += 1
    
    if current_part:
        parts.append(''.join(current_part))
    
    # Join parts with spaces, but filter out empty parts
    parts = [p for p in parts if p.strip()]
    stem = ' '.join(parts)
    
    # Step 7: Clean up and restore preserved patterns
    stem = stem.strip()
    
    # Restore parentheses patterns (try to maintain original position)
    # Insert them before quality/part indicators if those exist
    if paren_patterns:
        # Find where to insert - before quality/part indicators
        if quality_patterns or part_patterns:
            # Insert before the last word (which might be quality/part related)
            words = stem.split()
            if len(words) > 1:
                paren_text = ' '.join(pattern for _, _, pattern in paren_patterns)
                stem = ' '.join(words[:-1]) + ' ' + paren_text + ' ' + words[-1]
            else:
                paren_text = ' '.join(pattern for _, _, pattern in paren_patterns)
                stem = stem + ' ' + paren_text
        else:
            # No quality/part indicators, just append
            paren_text = ' '.join(pattern for _, _, pattern in paren_patterns)
            stem = stem + ' ' + paren_text if stem else paren_text
    
    # Restore quality indicators
    for start, end, pattern in quality_patterns:
        if stem:
            # Prefer hyphen before quality indicators, preserve original prefix
            if pattern.startswith('-'):
                stem = stem + pattern
            elif pattern.startswith('_'):
                stem = stem + ' ' + pattern[1:]
            else:
                # Add hyphen if not present
                stem = stem + '-' + pattern
        else:
            stem = pattern.lstrip('-_')
    
    # Restore part numbers
    for start, end, pattern in part_patterns:
        if stem:
            stem = stem + ' - ' + pattern
        else:
            stem = pattern
    
    # Clean up multiple spaces again after restoring patterns
    stem = re.sub(r'\s+', ' ', stem)
    stem = stem.strip()
    
    # If stem is empty after cleaning, use a default
    if not stem:
        stem = "download"
    
    # Step 9: Apply title case (capitalize first letter of each word)
    # But preserve common lowercase words unless they're the first word
    words = stem.split()
    normalized_words = []
    for i, word in enumerate(words):
        if not word:
            continue
        
        # Preserve quality indicators as-is (case-wise)
        if re.match(r'^\d+p$|^4K$|^8K$|^HD$|^SD$', word, re.IGNORECASE):
            # Preserve original case for 4K/8K, lowercase for others
            if word.upper() == '4K':
                normalized_words.append('4K')  # Always uppercase
            elif word.upper() == '8K':
                normalized_words.append('8K')  # Always uppercase
            else:
                normalized_words.append(word.lower())
            continue
        
        if word.startswith('Part') and re.match(r'^Part\s+\d+$', word, re.IGNORECASE):
            # Capitalize "Part" but keep number
            normalized_words.append('Part ' + word.split()[1] if len(word.split()) > 1 else word)
            continue
        
        # Preserve single/double digit numbers
        if re.match(r'^\d{1,2}$', word):
            normalized_words.append(word)
            continue
        
        # Keep common lowercase words lowercase unless they're the first word
        # But capitalize certain words in specific contexts
        lowercase_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        if i > 0 and word.lower() in lowercase_words:
            # Special cases for capitalization:
            # - "And" if connecting two capitalized words
            # - "The", "For", "Of" if they're part of a title (not articles)
            if word.lower() == 'and' and i > 0 and normalized_words:
                prev_word = normalized_words[-1]
                # Capitalize "And" if previous word is capitalized (not lowercase article)
                if prev_word and prev_word[0].isupper() and prev_word.lower() not in lowercase_words:
                    normalized_words.append('And')
                else:
                    normalized_words.append(word.lower())
            elif word.lower() in ('the', 'for', 'of') and i > 0 and normalized_words:
                prev_word = normalized_words[-1]
                # Capitalize if previous word is capitalized and it's not a simple article usage
                if prev_word and prev_word[0].isupper():
                    # Capitalize "The", "For", "Of" in titles
                    normalized_words.append(word.capitalize())
                else:
                    normalized_words.append(word.lower())
            else:
                normalized_words.append(word.lower())
        else:
            # Title case: capitalize first letter, lowercase the rest
            # But preserve apostrophes
            if "'" in word:
                # Handle contractions: "don't" -> "Don't"
                parts = word.split("'")
                if len(parts) == 2:
                    normalized_words.append(parts[0].capitalize() + "'" + parts[1].lower())
                else:
                    normalized_words.append(word.capitalize())
            else:
                normalized_words.append(word.capitalize())
    
    normalized_stem = ' '.join(normalized_words)
    
    # Final cleanup: remove any remaining double spaces
    normalized_stem = re.sub(r'\s+', ' ', normalized_stem).strip()
    
    # Reconstruct filename
    return normalized_stem + ext


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
