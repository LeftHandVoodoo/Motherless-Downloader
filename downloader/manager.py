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

        # Determine resume offset
        resume_offset = compute_resume_offset(final_path)

        # Debug print helper (defined before any use below)
        def _dbg(msg: str) -> None:
            try:
                print(f"[DL] {msg}", flush=True)
            except Exception:
                pass

        # HEAD validation and discovery
        page_url = req.url
        headers_common = {"User-Agent": "Mozilla/5.0", "Referer": page_url}
        # Prefer HTTP/2 when available, but fall back gracefully if 'h2' is not installed.
        allow_http2 = False
        try:
            import h2  # type: ignore  # noqa: F401
            allow_http2 = True
        except Exception:
            allow_http2 = False
            self.status.emit("HTTP/2 not available; falling back to HTTP/1.1 (install httpx[http2])")

        with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=headers_common, http2=allow_http2) as client:
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
                resume_offset = compute_resume_offset(final_path)

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

        # Prepare filesystem and preallocate .part
        final_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.parent.mkdir(parents=True, exist_ok=True)
        if not part_path.exists():
            with open(part_path, "wb") as fp:
                if total_size > 0:
                    fp.truncate(total_size)

        # Speed tracking
        window: list[tuple[float, int]] = []

        # Attempt resume if acceptable
        headers: dict[str, str] = {"User-Agent": "Mozilla/5.0", "Referer": page_url}
        if resume_offset > 0:
            headers["Range"] = f"bytes={resume_offset}-"

        bytes_received = resume_offset
        start_time = time.time()

        bytes_lock = threading.Lock()

        def download_range(seg_index: int, range_start: int, range_end: int) -> None:
            nonlocal bytes_received
            rng = f"bytes={range_start}-" if range_end < 0 else f"bytes={range_start}-{range_end}"
            hdrs = dict(headers)
            hdrs["Range"] = rng
            _dbg(f"seg#{seg_index} starting GET {req.url} with Range={rng}")
            with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=hdrs, http2=allow_http2) as client:
                with client.stream("GET", req.url) as resp:
                    if resp.status_code not in (200, 206):
                        _dbg(f"seg#{seg_index} unexpected status {resp.status_code}")
                        raise RuntimeError(f"Unexpected status {resp.status_code}")
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
                        for chunk in resp.iter_bytes(chunk_size=DEFAULT_CHUNK_SIZE):
                            if self._cancel_event.is_set():
                                self.finished.emit(False, "Cancelled")
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
                            state = make_sidecar_for_url(final_path, req.url, total_size, bytes_received)
                            # Serialize sidecar writes to avoid Windows rename contention
                            try:
                                with self._sidecar_lock:
                                    save_sidecar_atomic(sidecar_path, state)
                            except PermissionError:
                                # Best-effort: skip this update; try again on next chunk
                                _dbg("sidecar save skipped due to PermissionError (Windows contention)")
                            now = time.time()
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
                            self.progress.emit(bytes_received, total_size)
                        _dbg(f"seg#{seg_index} finished, downloaded {seg_bytes} bytes")

        attempt = 0
        while attempt <= MAX_RETRIES:
            if self._cancel_event.is_set():
                self.finished.emit(False, "Cancelled")
                return

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

        # Finalize
        if bytes_received != total_size:
            self.finished.emit(False, "Size mismatch; kept .part for resume")
            return

        # Move to final file atomically
        final_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.replace(final_path)
        # Cleanup sidecar
        try:
            build_sidecar_path(final_path).unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception:
            pass

        self.finished.emit(True, "Completed")
