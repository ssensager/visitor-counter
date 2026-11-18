"""Stream processed frames and encode them for MJPEG consumers."""

from __future__ import annotations

import threading
from collections import deque
from time import perf_counter
from typing import Iterator

import cv2
import numpy as np

from shared.contracts import VisitorCounterProtocol

from .video_source import VideoSource


class VideoProcessor:
    def __init__(self, counter: VisitorCounterProtocol) -> None:
        self._counter = counter

    def process(
        self, source: str, stop_event: threading.Event | None = None
    ) -> Iterator[tuple[np.ndarray, dict]]:
        """Yield processed frames with one-based frame indices and pipeline statistics."""
        self._counter.reset()
        if stop_event is None:
            stop_event = threading.Event()
        if stop_event.is_set():
            return

        durations: deque[float] = deque(maxlen=30)
        frame_index = 0
        video = VideoSource(source)
        try:
            total_frames = video.total_frames
            while not stop_event.is_set():
                start = perf_counter()
                ok, frame = video.read()
                if not ok or frame is None or stop_event.is_set():
                    break

                processed_frame, counter_stats = self._counter.process_frame(frame)
                durations.append(perf_counter() - start)
                if stop_event.is_set():
                    break

                frame_index += 1
                elapsed = sum(durations)
                stats = dict(
                    counter_stats,
                    fps=round(len(durations) / elapsed, 1) if elapsed > 0 else 0.0,
                    frame_index=frame_index,
                    progress=min(frame_index / total_frames, 1.0) if total_frames else None,
                )
                yield processed_frame, stats
        finally:
            video.release()


def encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode a frame as JPEG bytes with OpenCV's 0–100 quality setting."""
    if not 0 <= quality <= 100:
        raise ValueError("JPEG quality must be between 0 and 100")
    try:
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    except cv2.error as exc:
        raise ValueError("Could not encode frame as JPEG") from exc
    if not ok:
        raise ValueError("Could not encode frame as JPEG")
    return encoded.tobytes()
