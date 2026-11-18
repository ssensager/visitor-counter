from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch

import cv2
import numpy as np

from shared.contracts import VideoProcessorProtocol
from shared.mock_counter import MockVisitorCounter
from video import VideoProcessor, VideoSource, encode_jpeg

def main() -> None:
    processor = VideoProcessor(MockVisitorCounter())
    assert isinstance(processor, VideoProcessorProtocol)
    with TemporaryDirectory() as directory:
        for extension, codec in (("avi", "MJPG"), ("mp4", "mp4v")):
            path = str(Path(directory) / f"sample.{extension}")
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*codec), 20, (320, 240))
            try:
                assert writer.isOpened()
                for index in range(35):
                    writer.write(np.full((240, 320, 3), index, dtype=np.uint8))
            finally:
                writer.release()

            with VideoSource(path) as source:
                assert (source.width, source.height, source.total_frames, source.fps) == (320, 240, 35, 20)
                assert source.read()[0]
            assert source.read() == (False, None)

            def run(stop=None):
                source = VideoSource(path)
                with patch("video.frame_stream.VideoSource", return_value=source):
                    with closing(processor.process(path, stop)) as frames:
                        for index, (frame, stats) in enumerate(frames, 1):
                            assert frame.shape == (240, 320, 3)
                            assert {"entered", "exited", "current", "people", "fps", "frame_index", "progress"} <= stats.keys()
                            assert stats["frame_index"] == index
                            assert stats["progress"] == index / 35
                            assert isinstance(stats["fps"], float) and stats["fps"] >= 0
                            assert stats["entered"] == int(index >= 30)
                            assert encode_jpeg(frame).startswith(b"\xff\xd8")
                            if stop is not None:
                                stop.set()
                assert source.read() == (False, None)
                return index

            assert run() == 35
            assert run(Event()) == 1

            for fail in (False, True):
                source = VideoSource(path)
                with patch("video.frame_stream.VideoSource", return_value=source):
                    with closing(processor.process(path)) as frames:
                        if fail:
                            with patch.object(MockVisitorCounter, "process_frame", side_effect=RuntimeError("counter failure")):
                                try:
                                    next(frames)
                                except RuntimeError as exc:
                                    assert str(exc) == "counter failure"
                                else:
                                    raise AssertionError("Counter error did not propagate")
                        else:
                            next(frames)
                assert source.read() == (False, None)

            with patch.object(VideoSource, "total_frames", None):
                with closing(processor.process(path)) as frames:
                    assert next(frames)[1]["progress"] is None
            print(f"{extension.upper()}: 35 frames, stats, JPEG, stop, close, error cleanup, unknown progress OK")

        try:
            VideoSource(str(Path(directory) / "missing.avi"))
        except OSError as exc:
            assert "missing.avi" in str(exc)
        else:
            raise AssertionError("Missing file was opened")
        print("Missing source: OK")


if __name__ == "__main__":
    main()
