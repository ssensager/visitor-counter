"""OpenCV video input and frame processing."""

from .frame_stream import VideoProcessor, encode_jpeg
from .video_source import VideoSource

__all__ = ["VideoSource", "VideoProcessor", "encode_jpeg"]
