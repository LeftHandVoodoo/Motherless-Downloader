from __future__ import annotations

from typing import List, Tuple


def compute_segments(total_size: int, num_connections: int) -> List[Tuple[int, int]]:
    if total_size <= 0:
        return [(0, -1)]
    if num_connections <= 1:
        return [(0, total_size - 1)]
    size_per = total_size // num_connections
    remainder = total_size % num_connections
    segments: List[Tuple[int, int]] = []
    start = 0
    for i in range(num_connections):
        span = size_per + (1 if i < remainder else 0)
        end = start + span - 1
        segments.append((start, end))
        start = end + 1
    return segments


def adjust_segments_for_resume(segments: List[Tuple[int, int]], resume_offset: int) -> List[Tuple[int, int]]:
    if resume_offset <= 0:
        return segments
    adjusted: List[Tuple[int, int]] = []
    for start, end in segments:
        if resume_offset > end:
            continue
        if resume_offset > start:
            start = resume_offset
        adjusted.append((start, end))
    return adjusted
