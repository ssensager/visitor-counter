"""Adapters for the shared protocols; inference never runs on the ASGI loop."""

import importlib
import logging
import os
import time

from backend.services.job_manager import Job, JobError, JobManager
from shared.contracts import LineSegment
from shared.mock_counter import MockVisitorCounter

logger = logging.getLogger(__name__)


def exported_class(module_name: str, name: str):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise  # A broken installed module must not silently become a mock.
    return getattr(module, name, None)


class MockVideoProcessor:
    """Simple paced file reader used only with the fake counter."""

    def __init__(self, counter):
        self.counter = counter

    def process(self, source, stop_event):
        import cv2

        capture = cv2.VideoCapture(source)
        try:
            if not capture.isOpened():
                raise ValueError("Не удалось открыть видео")
            fps = capture.get(cv2.CAP_PROP_FPS)
            fps = fps if 0 < fps <= 240 else 25.0
            total = capture.get(cv2.CAP_PROP_FRAME_COUNT)
            index = 0
            while not stop_event.is_set():
                started = time.perf_counter()
                ok, frame = capture.read()
                if not ok:
                    if index == 0:
                        raise ValueError("Видео не содержит читаемых кадров")
                    break
                frame, stats = self.counter.process_frame(frame)
                index += 1
                elapsed = max(time.perf_counter() - started, 1e-6)
                stats.update(fps=round(1 / elapsed, 2), frame_index=index,
                             progress=min(index / total, 1.0) if total > 0 else None)
                yield frame, stats
                stop_event.wait(max(0, 1 / fps - (time.perf_counter() - started)))
        finally:
            capture.release()


class VideoService:
    def __init__(self, manager: JobManager):
        self.manager = manager
        self._counter = None
        self._processor_class = None

    def _processor(self, line):
        if self._counter is None:
            use_mock = os.getenv("VISITOR_USE_MOCK", "0") == "1"
            counter_class = None if use_mock else exported_class("ml", "VisitorCounter")
            processor_class = None if use_mock else exported_class("video", "VideoProcessor")
            if counter_class is None or processor_class is None:
                logger.warning("Using MOCK processing (explicit setting or missing ml/video exports)")
                counter_class, processor_class = MockVisitorCounter, MockVideoProcessor
            self._counter = counter_class()
            self._processor_class = processor_class
        self._counter.reset()
        # _run sets the requested line or derives the default from this video's dimensions.
        return self._processor_class(self._counter), line

    def start(self, job_id: str, line: LineSegment | None = None):
        self.manager.start(job_id, line, self._run)

    def stop(self, job_id: str):
        thread = self.manager.request_stop(job_id)
        if thread:
            thread.join(timeout=5)
            if thread.is_alive():
                raise JobError(409, "Остановка запрошена; обработка ещё завершает текущий кадр")

    def _run(self, job: Job, line):
        error = None
        iterator = None
        try:
            import cv2

            processor, line = self._processor(line)
            if line is None:
                # Probe only dimensions; no custom detection/counting logic here.
                capture = cv2.VideoCapture(str(job.path))
                try:
                    ok, first = capture.read()
                    if not ok:
                        raise ValueError("Не удалось прочитать видео")
                    height, width = first.shape[:2]
                    line = ((0, height // 2), (width, height // 2))
                finally:
                    capture.release()
            self._counter.set_line(*line)
            iterator = processor.process(str(job.path), stop_event=job.stop_event)
            count = 0
            for frame, stats in iterator:
                if job.stop_event.is_set():
                    break
                ok, encoded = cv2.imencode(".jpg", frame)
                if not ok:
                    raise ValueError("Не удалось кодировать кадр")
                self.manager.publish(job.job_id, encoded.tobytes(), stats)
                count += 1
            if count == 0 and not job.stop_event.is_set():
                raise ValueError("Видео не содержит обработанных кадров")
        except Exception:
            logger.exception("Processing failed for job %s", job.job_id)
            error = "Ошибка обработки видео. Проверьте файл и серверный журнал."
        finally:
            try:
                if iterator is not None and hasattr(iterator, "close"):
                    iterator.close()
            except Exception:
                logger.exception("Failed to release video iterator")
                error = "Ошибка освобождения видеоресурсов"
            self.manager.finish(job.job_id, error)
