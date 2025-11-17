from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple
from urllib.parse import urlparse
import time
import threading

import httpx
from PySide6.QtCore import QThread, Signal

from .utils import perform_head_validation, validate_url, sanitize_title_for_fs
from .discover import discover_media_url, discover_title
from .segments import compute_segments, adjust_segments_for_resume
from .state import (
    build_part_path,
    build_sidecar_path,
    compute_resume_offset,
    make_sidecar_for_url,
    save_sidecar_atomic,
    load_sidecar,
    sidecar_matches_url,
)


DEFAULT_CHUNK_SIZE = 1024 * 1024 * 2  # 2 MB
TARGET_TOTAL_BPS = 4_000_000  # Aim ~4 MB/s total if server permits
DEFAULT_TIMEOUT = httpx.Timeout(10.0, read=15.0)
MAX_RETRIES = 5
BACKOFF_INITIAL = 0.5

# Check HTTP/2 availability once at module load
HTTP2_AVAILABLE = False
try:
    import h2  # type: ignore  # noqa: F401
    HTTP2_AVAILABLE = True
except ImportError:
    pass


@dataclass
class DownloadRequest:
    url: str
    dest_file: Path
    explicit_filename: Optional[str] = None
    connections: int = 1
    adaptive_connections: bool = False


class DownloadManager(QThread):
    progress = Signal(int, int)  # bytes_received, total
    speed = Signal(float)  # bytes/sec
    status = Signal(str)
    head_info = Signal(int, bool, str, str)  # total_bytes, accept_ranges, content_type, suggested_filename
    finished = Signal(bool, str)

    def __init__(self, request: DownloadRequest, parent=None) -> None:
        super().__init__(parent)
        self._request = request
        self._pause_event = threading.Event()
        self._cancel_event = threading.Event()
        self._pause_event.set()  # start unpaused
        self._sidecar_lock = threading.Lock()

    def pause(self) -> None:
        self._pause_event.clear()
        self.status.emit("Paused")

    def resume(self) -> None:
        self._pause_event.set()
        self.status.emit("Resumed")

    def cancel(self) -> None:
        self._cancel_event.set()
        self.status.emit("Cancelling…")

    def run(self) -> None:  # type: ignore[override]
        try:
            self._run_impl()
        except Exception as exc:  # pragma: no cover - unexpected
            self.finished.emit(False, f"Error: {exc}")

    def _run_impl(self) -> None:
        req = self._request
        url_ok = validate_url(req.url)
        if not url_ok.is_valid:
            self.finished.emit(False, url_ok.message)
            return

        final_path = req.dest_file
        part_path = build_part_path(final_path)
        sidecar_path = build_sidecar_path(final_path)

        # Validate resume state matches URL
        resume_offset = 0
        existing_sidecar = load_sidecar(sidecar_path)
        if existing_sidecar:
            if sidecar_matches_url(existing_sidecar, req.url):
                # Valid resume - use existing progress
                resume_offset = compute_resume_offset(final_path)
                self.status.emit(f"Resuming from {resume_offset} bytes")
            else:
                # URL mismatch - start fresh
                self.status.emit("Previous download was for different URL; starting fresh")
                try:
                    part_path.unlink(missing_ok=True)  # type: ignore[arg-type]
                    sidecar_path.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:
                    pass
                resume_offset = 0
        else:
            # No sidecar - check if part file exists anyway
            resume_offset = compute_resume_offset(final_path)
            if resume_offset > 0:
                self.status.emit(f"Found partial download ({resume_offset} bytes) but no resume data; starting fresh")
                try:
                    part_path.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:
                    pass
                resume_offset = 0

        # Debug print helper (defined before any use below)
        def _dbg(msg: str) -> None:
            try:
                print(f"[DL] {msg}", flush=True)
            except Exception:
                pass

        # HEAD validation and discovery
        page_url = req.url
        headers_common = {"User-Agent": "Mozilla/5.0", "Referer": page_url}

        # Emit HTTP/2 status message only once per session
        if not HTTP2_AVAILABLE:
            self.status.emit("HTTP/2 not available; using HTTP/1.1 (install httpx[http2] for HTTP/2 support)")

        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=headers_common, http2=HTTP2_AVAILABLE) as client:
            page_title: Optional[str] = None
            # First, try HEAD on provided URL
            head_resp = client.head(req.url, follow_redirects=True)
            _dbg(f"HEAD status={head_resp.status_code} url={req.url}")
            try:
                ar = head_resp.headers.get("Accept-Ranges")
                cl = head_resp.headers.get("Content-Length")
                cr = head_resp.headers.get("Content-Range")
                ra = head_resp.headers.get("Retry-After")
                sv = head_resp.headers.get("Server")
                _dbg(f"HEAD headers: Accept-Ranges={ar} Content-Length={cl} Content-Range={cr} Retry-After={ra} Server={sv}")
            except Exception:
                pass
            head = perform_head_validation(head_resp.status_code, dict(head_resp.headers))
            if not head.is_valid:
                # Fallback: GET page and discover media source URL
                page = client.get(req.url, follow_redirects=True)
                _dbg(f"GET page status={page.status_code} url={req.url}")
                media = discover_media_url(page.text) if page.status_code == 200 else None
                if not media:
                    self.finished.emit(False, head.message)
                    return
                # Resolve relative media URL against page URL
                from urllib.parse import urljoin
                media_url = urljoin(str(page.url), media)
                # Retry HEAD on media URL
                head_resp = client.head(media_url, follow_redirects=True)
                _dbg(f"HEAD media status={head_resp.status_code} media={media_url}")
                head = perform_head_validation(head_resp.status_code, dict(head_resp.headers))
                if not head.is_valid:
                    self.finished.emit(False, head.message)
                    return
                # Replace request URL with discovered media URL
                req.url = media_url  # type: ignore[misc]
                # Try to extract a title and build a subfolder
                title = discover_title(page.text)
                if title:
                    page_title = sanitize_title_for_fs(title)
            total_size = head.total_bytes or 0
            fallback_name = Path(urlparse(req.url).path).name or "download.bin"
            suggested = head.suggested_filename or fallback_name
            suggested_for_ui = page_title or suggested
            self.head_info.emit(total_size, bool(head.accept_ranges_bytes), head.content_type or "", suggested_for_ui)

            # If the caller did not request an explicit filename, choose a better
            # final filename based on HEAD information (suggested name and content type).
            if req.explicit_filename is None:
                def _apply_ext(name: str, content_type: str) -> str:
                    ct = (content_type or "").split(";")[0].strip().lower()
                    ext_map = {
                        "video/mp4": ".mp4",
                        "video/webm": ".webm",
                        "video/x-matroska": ".mkv",
                        "video/quicktime": ".mov",
                        "video/x-msvideo": ".avi",
                        "video/mpeg": ".mpeg",
                        "video/mp2t": ".ts",
                        "video/ogg": ".ogv",
                        "video/x-flv": ".flv",
                    }
                    from pathlib import Path as _Path
                    p = _Path(name)
                    stem = p.stem
                    ext = p.suffix.lower()
                    # Only override when there's no meaningful extension
                    if ext in ("", ".bin"):
                        mapped = ext_map.get(ct)
                        if mapped:
                            return stem + mapped
                    return name

                base_name = page_title or suggested
                target_name = _apply_ext(base_name, head.content_type or "")
                # Update final path and dependent paths to use the chosen filename
                final_path = final_path.with_name(target_name)
                part_path = build_part_path(final_path)
                sidecar_path = build_sidecar_path(final_path)
                # Re-validate resume state for new filename
                existing_sidecar = load_sidecar(sidecar_path)
                if existing_sidecar and sidecar_matches_url(existing_sidecar, req.url):
                    resume_offset = compute_resume_offset(final_path)
                    self.status.emit(f"Resuming from {resume_offset} bytes")
                else:
                    resume_offset = 0

            # Optional: adapt connections to server-permitted rate only if requested
            if self._request.adaptive_connections:
                try:
                    from urllib.parse import parse_qs
                    qs = parse_qs(urlparse(req.url).query)
                    rate_v = (qs.get("rate", [None])[0])
                    per_conn_bps = None
                    if rate_v:
                        rv = str(rate_v).lower().rstrip()
                        if rv.endswith("k"):
                            num = float(rv[:-1])
                            per_conn_bps = (num * 1000.0) / 8.0  # kbit -> bytes/s
                        else:
                            num = float(rv)
                            per_conn_bps = num  # assume bytes/s if plain number
                    if per_conn_bps:
                        est = int(per_conn_bps)
                        _dbg(f"server hint: per-connection ~{est/1024:.1f} KB/s from rate={rate_v}")
                        # Compute recommended concurrency to target TARGET_TOTAL_BPS (bounded by user request)
                        recommended = max(1, min(30, int((TARGET_TOTAL_BPS / max(1.0, per_conn_bps)))))
                        if recommended != self._request.connections:
                            _dbg(f"auto-adjusting connections to {recommended} (was {self._request.connections}) to compensate for throttle")
                            self._request.connections = recommended
                except Exception:
                    pass

        # Prepare filesystem and validate permissions
        try:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            part_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            self.finished.emit(False, f"Permission denied: Cannot create directory {final_path.parent}")
            return
        except Exception as e:
            self.finished.emit(False, f"Failed to create directory: {e}")
            return

        # Test write permissions by creating/opening the part file
        try:
            if not part_path.exists():
                with open(part_path, "wb") as fp:
                    if total_size > 0:
                        fp.truncate(total_size)
            else:
                # Test that we can open existing file for writing
                with open(part_path, "r+b"):
                    pass
        except PermissionError:
            self.finished.emit(False, f"Permission denied: Cannot write to {part_path}")
            return
        except Exception as e:
            self.finished.emit(False, f"Failed to access download file: {e}")
            return

        # Speed tracking
        window: list[tuple[float, int]] = []
        window_lock = threading.Lock()

        # Attempt resume if acceptable
        headers: dict[str, str] = {"User-Agent": "Mozilla/5.0", "Referer": page_url}
        if resume_offset > 0:
            headers["Range"] = f"bytes={resume_offset}-"

        bytes_received = resume_offset
        start_time = time.time()

        bytes_lock = threading.Lock()
        download_failed = threading.Event()

        def download_range(seg_index: int, range_start: int, range_end: int) -> None:
            nonlocal bytes_received
            # Early exit if cancelled or failed
            if self._cancel_event.is_set() or download_failed.is_set():
                return

            rng = f"bytes={range_start}-" if range_end < 0 else f"bytes={range_start}-{range_end}"
            hdrs = dict(headers)
            hdrs["Range"] = rng
            _dbg(f"seg#{seg_index} starting GET {req.url} with Range={rng}")
            try:
                with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=hdrs, http2=HTTP2_AVAILABLE) as client:
                    with client.stream("GET", req.url) as resp:
                        if resp.status_code not in (200, 206):
                            _dbg(f"seg#{seg_index} unexpected status {resp.status_code}")
                            download_failed.set()
                            raise RuntimeError(f"Segment {seg_index}: Unexpected status {resp.status_code}")
                        # Inspect throttling hints
                        try:
                            cr = resp.headers.get("Content-Range")
                            ra = resp.headers.get("Retry-After")
                            sv = resp.headers.get("Server")
                            _dbg(f"seg#{seg_index} headers: Content-Range={cr} Retry-After={ra} Server={sv}")
                        except Exception:
                            pass
                        mode = "r+b" if part_path.exists() else "wb"
                        with open(part_path, mode) as fp:
                            fp.seek(range_start)
                            seg_bytes = 0
                            first_chunk_time = None
                            last_log_time = time.time()
                            last_sidecar_time = time.time()
                            last_progress_time = 0.0  # Throttle progress emissions
                            for chunk in resp.iter_bytes(chunk_size=DEFAULT_CHUNK_SIZE):
                                # Check cancel and failure flags
                                if self._cancel_event.is_set() or download_failed.is_set():
                                    return
                                self._pause_event.wait()
                                if not chunk:
                                    continue
                                fp.write(chunk)
                                with bytes_lock:
                                    bytes_received += len(chunk)
                                seg_bytes += len(chunk)
                                if first_chunk_time is None:
                                    first_chunk_time = time.time()

                                now = time.time()
                                # Throttle sidecar writes to every 2 seconds to reduce I/O
                                if now - last_sidecar_time >= 2.0:
                                    state = make_sidecar_for_url(final_path, req.url, total_size, bytes_received)
                                    # Serialize sidecar writes to avoid Windows rename contention
                                    try:
                                        with self._sidecar_lock:
                                            save_sidecar_atomic(sidecar_path, state)
                                        last_sidecar_time = now
                                    except PermissionError:
                                        # Best-effort: skip this update; try again on next chunk
                                        _dbg("sidecar save skipped due to PermissionError (Windows contention)")

                                # Thread-safe speed tracking
                                with window_lock:
                                    window.append((now, bytes_received))
                                    window[:] = [w for w in window if now - w[0] <= 3.0]
                                    if len(window) >= 2:
                                        dt = window[-1][0] - window[0][0]
                                        ds = window[-1][1] - window[0][1]
                                        if dt > 0:
                                            self.speed.emit(ds / dt)

                                # periodic per-seg throughput debug
                                if now - last_log_time >= 2.0 and first_chunk_time is not None:
                                    dur = now - first_chunk_time
                                    bps = seg_bytes / max(dur, 1e-6)
                                    _dbg(f"seg#{seg_index} avg {bps/1024:.1f} KB/s over {dur:.1f}s")
                                    last_log_time = now
                                
                                # Throttle progress emissions to ~10 times per second per segment
                                # With multiple segments, total emission rate is still reasonable
                                if now - last_progress_time >= 0.1:
                                    self.progress.emit(bytes_received, total_size)
                                    last_progress_time = now
                            _dbg(f"seg#{seg_index} finished, downloaded {seg_bytes} bytes")
            except Exception as e:
                download_failed.set()
                _dbg(f"seg#{seg_index} failed: {e}")
                raise

        attempt = 0
        while attempt <= MAX_RETRIES:
            if self._cancel_event.is_set():
                self.finished.emit(False, "Cancelled by user")
                return

            # Reset failure flag for this attempt
            download_failed.clear()

            try:
                # Multi-connection segmented download
                conns = max(1, min(30, req.connections))
                _dbg(f"Using {conns} connections; total_size={total_size}; resume_offset={resume_offset}")
                if conns == 1:
                    # Preflight single range
                    download_range(0, resume_offset, -1)
                else:
                    segs = compute_segments(total_size, conns)
                    segs = adjust_segments_for_resume(segs, resume_offset)
                    if not segs:
                        # Nothing left
                        break
                    _dbg(f"Computed {len(segs)} segments; first 5: {segs[:5]}")
                    threads: list[threading.Thread] = []
                    for idx, (s, e) in enumerate(segs):
                        t = threading.Thread(target=download_range, args=(idx, s, e), daemon=True)
                        threads.append(t)
                        t.start()
                    for t in threads:
                        t.join()

                # Check if cancelled or failed during download
                if self._cancel_event.is_set():
                    self.finished.emit(False, "Cancelled by user")
                    return
                if download_failed.is_set():
                    raise RuntimeError("One or more download segments failed")

                break  # success
            except Exception as exc:
                attempt += 1
                if attempt > MAX_RETRIES:
                    self.finished.emit(False, f"Failed after retries: {exc}")
                    return
                backoff = BACKOFF_INITIAL * (2 ** (attempt - 1))
                self.status.emit(f"Retrying in {backoff:.1f}s: {exc}")
                _dbg(f"retry {attempt}/{MAX_RETRIES} after error: {exc}; sleeping {backoff:.1f}s")
                time.sleep(backoff)

        # Finalize - save final state
        try:
            state = make_sidecar_for_url(final_path, req.url, total_size, bytes_received)
            with self._sidecar_lock:
                save_sidecar_atomic(sidecar_path, state)
        except Exception as e:
            _dbg(f"Failed to save final sidecar state: {e}")

        if bytes_received != total_size:
            self.finished.emit(False, f"Download incomplete: {bytes_received}/{total_size} bytes received. Resume data saved.")
            return

        # Emit final progress to ensure 100% is shown
        self.progress.emit(total_size, total_size)
        
        # Move to final file atomically
        final_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.replace(final_path)
        # Cleanup sidecar
        try:
            build_sidecar_path(final_path).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass

        self.finished.emit(True, "Download completed successfully")
