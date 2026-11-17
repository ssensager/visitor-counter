"""Dependency-free mock implementation of VisitorCounterProtocol.

Allows Video, Backend, and Frontend developers to run end-to-end tests
before the real YOLOv8n + ByteTrack module is merged.
"""

from __future__ import annotations

from typing import Any

from .contracts import FrameStats, LineSegment, PersonDetection, Point2D


class MockVisitorCounter:
    """Deterministic fake counter simulating people crossing a virtual line."""

    def __init__(
        self,
        model_path: str | None = None,
        line: LineSegment | None = None,
        conf_threshold: float = 0.35,
    ) -> None:
        self.model_path = model_path
        self.line = line
        self.conf_threshold = conf_threshold
        self._frame_count = 0
        self._entered = 0
        self._exited = 0

    def set_line(self, p1: Point2D, p2: Point2D) -> None:
        self.line = (p1, p2)

    def reset(self) -> None:
        self._frame_count = 0
        self._entered = 0
        self._exited = 0

    def process_frame(self, frame: Any) -> tuple[Any, dict[str, Any]]:
        self._frame_count += 1

        # Simulate periodic crossings so live UI updates are clearly visible.
        if self._frame_count % 30 == 0:
            self._entered += 1
        elif self._frame_count % 55 == 0:
            self._exited += 1

        bbox = [120, 80 + (self._frame_count * 4) % 200, 210, 220 + (self._frame_count * 4) % 200]
        output_frame = frame.copy() if hasattr(frame, "copy") else frame

        self._draw_overlay(output_frame, bbox)

        stats = FrameStats(
            entered=self._entered,
            exited=self._exited,
            current=self._entered - self._exited,
            people=[PersonDetection(id=1, bbox=bbox)],
        ).to_ml_dict()
        return output_frame, stats

    def _draw_overlay(self, frame: Any, bbox: list[int]) -> None:
        """Draw mock box and virtual line if OpenCV and array shape are available."""
        if not hasattr(frame, "shape") or len(frame.shape) < 2:
            return
        try:
            import cv2  # type: ignore
        except ImportError:
            return

        height, width = int(frame.shape[0]), int(frame.shape[1])
        line = self.line or ((0, height // 2), (width, height // 2))

        cv2.line(frame, line[0], line[1], (0, 255, 255), 2)
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 220, 120), 2)
        cv2.putText(
            frame,
            f"MOCK ID:1 | IN:{self._entered} OUT:{self._exited}",
            (bbox[0], max(20, bbox[1] - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 220, 120),
            2,
        )
