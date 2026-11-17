"""Shared contracts, constants, and mock implementations for visitor-counter."""

from .contracts import (
    ALLOWED_VIDEO_EXTENSIONS,
    JOB_STATUSES,
    FrameStats,
    PersonDetection,
    VideoProcessorProtocol,
    VisitorCounterProtocol,
)
from .mock_counter import MockVisitorCounter

__all__ = [
    "ALLOWED_VIDEO_EXTENSIONS",
    "JOB_STATUSES",
    "FrameStats",
    "PersonDetection",
    "VisitorCounterProtocol",
    "VideoProcessorProtocol",
    "MockVisitorCounter",
]
