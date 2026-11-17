"""Canonical data contracts and module protocols for visitor-counter.

Keep this module free of heavy third-party dependencies (torch, ultralytics, cv2, fastapi)
so every team module can import it independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, Protocol, runtime_checkable

ALLOWED_VIDEO_EXTENSIONS: tuple[str, ...] = (".mp4", ".avi")

JobStatusType = Literal["uploaded", "processing", "completed", "stopped", "error"]
JOB_STATUSES: tuple[str, ...] = ("uploaded", "processing", "completed", "stopped", "error")

Point2D = tuple[int, int]
LineSegment = tuple[Point2D, Point2D]


@dataclass(slots=True)
class PersonDetection:
    """Single tracked person detected on a frame."""

    id: int
    bbox: list[int]  # [x1, y1, x2, y2] in pixel coordinates

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": int(self.id),
            "bbox": [int(v) for v in self.bbox],
        }


@dataclass(slots=True)
class FrameStats:
    """Statistics returned by VisitorCounter and enriched by VideoProcessor."""

    entered: int = 0
    exited: int = 0
    current: int = 0
    people: list[PersonDetection] = field(default_factory=list)
    fps: float | None = None
    frame_index: int | None = None
    progress: float | None = None

    def to_ml_dict(self) -> dict[str, Any]:
        """Minimal stats dictionary produced by the ML module."""
        return {
            "entered": int(self.entered),
            "exited": int(self.exited),
            "current": int(self.current),
            "people": [person.to_dict() for person in self.people],
        }

    def to_dict(self) -> dict[str, Any]:
        """Full stats dictionary including optional video-pipeline metadata."""
        data = self.to_ml_dict()
        if self.fps is not None:
            data["fps"] = round(float(self.fps), 2)
        if self.frame_index is not None:
            data["frame_index"] = int(self.frame_index)
        if self.progress is not None:
            data["progress"] = round(float(self.progress), 4)
        return data


@runtime_checkable
class VisitorCounterProtocol(Protocol):
    """Interface that ml.VisitorCounter must implement."""

    def set_line(self, p1: Point2D, p2: Point2D) -> None: ...

    def process_frame(self, frame: Any) -> tuple[Any, dict[str, Any]]: ...

    def reset(self) -> None: ...


@runtime_checkable
class VideoProcessorProtocol(Protocol):
    """Interface that video.VideoProcessor must implement."""

    def process(
        self,
        source: str,
        stop_event: Any | None = None,
    ) -> Iterator[tuple[Any, dict[str, Any]]]: ...
