from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import json
import os
import tempfile

from .utils import get_url_hash


SIDECAR_SUFFIX = ".part.json"
PART_SUFFIX = ".part"


@dataclass(frozen=True)
class SidecarState:
    url_hash: str
    total_size: int
    received_bytes: int


def build_part_path(final_path: Path) -> Path:
    return final_path.with_name(final_path.name + PART_SUFFIX)


def build_sidecar_path(final_path: Path) -> Path:
    return final_path.with_name(final_path.name + SIDECAR_SUFFIX)


def load_sidecar(sidecar_path: Path) -> Optional[SidecarState]:
    if not sidecar_path.exists():
        return None
    try:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        return SidecarState(
            url_hash=str(data.get("url_hash", "")),
            total_size=int(data.get("total_size", 0)),
            received_bytes=int(data.get("received_bytes", 0)),
        )
    except Exception:
        return None


def save_sidecar_atomic(sidecar_path: Path, state: SidecarState) -> None:
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "url_hash": state.url_hash,
        "total_size": state.total_size,
        "received_bytes": state.received_bytes,
    }
    fd, tmp_path_str = tempfile.mkstemp(prefix=sidecar_path.name, dir=str(sidecar_path.parent))
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(payload, fp)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tmp_path, sidecar_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def compute_resume_offset(final_path: Path) -> int:
    part_path = build_part_path(final_path)
    return part_path.stat().st_size if part_path.exists() else 0


def make_sidecar_for_url(final_path: Path, url: str, total_size: int, received_bytes: int) -> SidecarState:
    return SidecarState(url_hash=get_url_hash(url), total_size=total_size, received_bytes=received_bytes)


def sidecar_matches_url(state: SidecarState, url: str) -> bool:
    return state.url_hash == get_url_hash(url)
