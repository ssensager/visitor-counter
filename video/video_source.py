"""Read frames and metadata from an OpenCV video source."""

from __future__ import annotations

from math import isfinite

import cv2
import numpy as np


class VideoSource:
    def __init__(self, source: str) -> None:
        self._capture = cv2.VideoCapture(source)
        if not self._capture.isOpened():
            self.release()
            raise OSError(f"Could not open video source {source!r}")

    @property
    def fps(self) -> float:
        return self._capture.get(cv2.CAP_PROP_FPS)

    @property
    def width(self) -> int:
        return int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))

    @property
    def height(self) -> int:
        return int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    @property
    def total_frames(self) -> int | None:
        count = self._capture.get(cv2.CAP_PROP_FRAME_COUNT)
        return int(count) if isfinite(count) and count >= 1 else None

    def read(self) -> tuple[bool, np.ndarray | None]:
        ok, frame = self._capture.read()
        return (True, frame) if ok and frame is not None else (False, None)

    def release(self) -> None:
        self._capture.release()

    def __enter__(self) -> VideoSource:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()
