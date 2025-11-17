"""Downloader package for Motherless Single Downloader.

Exposes URL and header validation helpers used by the GUI and download engine.
"""
from .utils import (
    ALLOWED_HOST_SUFFIXES,
    UrlValidationResult,
    HeadValidationResult,
    is_https_url,
    is_allowed_host,
    validate_url,
    extract_filename_from_content_disposition,
    perform_head_validation,
    get_url_hash,
)
from .state import (
    SidecarState,
    build_part_path,
    build_sidecar_path,
    load_sidecar,
    save_sidecar_atomic,
    compute_resume_offset,
)

__all__ = [
    "ALLOWED_HOST_SUFFIXES",
    "UrlValidationResult",
    "HeadValidationResult",
    "is_https_url",
    "is_allowed_host",
    "validate_url",
    "extract_filename_from_content_disposition",
    "perform_head_validation",
    "get_url_hash",
    "SidecarState",
    "build_part_path",
    "build_sidecar_path",
    "load_sidecar",
    "save_sidecar_atomic",
    "compute_resume_offset",
]
