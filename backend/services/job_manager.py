"""In-process job registry. Run the application with exactly one worker."""

from dataclasses import dataclass, field
from pathlib import Path
from threading import Event, RLock, Thread
from typing import BinaryIO, Callable
from uuid import uuid4

from backend.schemas.responses import StatsResponse, UploadResponse
from shared.contracts import ALLOWED_VIDEO_EXTENSIONS, LineSegment


class JobError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class Job:
    job_id: str
    filename: str
    path: Path
    stats: StatsResponse
    jpeg: bytes | None = None
    revision: int = 0
    generation: int = 0
    stop_event: Event = field(default_factory=Event)
    thread: Thread | None = None


class JobManager:
    def __init__(self, upload_dir: Path, max_upload_bytes: int = 512 * 1024 * 1024):
        self.upload_dir = upload_dir
        self.max_upload_bytes = max_upload_bytes
        self._lock = RLock()
        self._jobs: dict[str, Job] = {}
        self._active: str | None = None
        self._closing = False

    def _get(self, job_id: str) -> Job:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise JobError(404, "Задача не найдена") from None

    def upload(self, filename: str | None, source: BinaryIO) -> UploadResponse:
        # Both POSIX and Windows client filenames are stripped; storage uses UUIDs.
        name = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        extension = Path(name).suffix.lower()
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise JobError(415, "Разрешены только файлы .mp4 и .avi")
        job_id = uuid4().hex
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        path = self.upload_dir / f"{job_id}{extension}"
        size = 0
        try:
            with path.open("xb") as target:
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_upload_bytes:
                        raise JobError(413, "Превышен максимальный размер видео")
                    target.write(chunk)
            if size == 0:
                raise JobError(400, "Видео не должно быть пустым")
            with self._lock:
                if self._closing:
                    raise JobError(503, "Сервер завершает работу")
                self._jobs[job_id] = Job(job_id, name, path, StatsResponse(job_id=job_id))
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return UploadResponse(job_id=job_id, filename=name)

    def snapshot(self, job_id: str) -> tuple[StatsResponse, bytes | None, int, int]:
        with self._lock:
            job = self._get(job_id)
            return job.stats.model_copy(deep=True), job.jpeg, job.revision, job.generation

    def start(self, job_id: str, line: LineSegment | None, worker: Callable) -> None:
        with self._lock:
            job = self._get(job_id)
            if self._closing:
                raise JobError(503, "Сервер завершает работу")
            if self._active is not None:
                raise JobError(409, "Уже запущена задача обработки")
            job.stop_event = Event()
            job.jpeg = None
            job.generation += 1
            job.revision += 1
            job.stats = StatsResponse(job_id=job_id, status="processing")
            self._active = job_id
            job.thread = Thread(target=worker, args=(job, line), daemon=True,
                                name=f"video-{job_id}")
            try:
                job.thread.start()
            except Exception:
                self._active = None
                job.stats.status = "error"
                job.stats.error = "Не удалось запустить обработку"
                job.revision += 1
                raise JobError(500, job.stats.error) from None

    def publish(self, job_id: str, jpeg: bytes, values: dict) -> None:
        with self._lock:
            job = self._get(job_id)
            job.stats = StatsResponse(
                job_id=job_id, entered=values["entered"], exited=values["exited"],
                current=values["current"], fps=values.get("fps", 0.0),
                progress=values.get("progress"), status="processing",
            )
            job.jpeg = jpeg
            job.revision += 1

    def finish(self, job_id: str, error: str | None = None) -> None:
        with self._lock:
            job = self._get(job_id)
            job.stats.status = "error" if error else (
                "stopped" if job.stop_event.is_set() else "completed")
            job.stats.error = error
            if job.stats.status == "completed":
                job.stats.progress = 1.0
            job.revision += 1
            self._active = None

    def request_stop(self, job_id: str) -> Thread | None:
        with self._lock:
            job = self._get(job_id)
            if job.stats.status == "stopped":
                return None  # Repeated stop is idempotent.
            if job.stats.status != "processing":
                raise JobError(409, "Задача не запущена")
            job.stop_event.set()
            return job.thread

    def shutdown(self) -> None:
        with self._lock:
            self._closing = True
            threads = [j.thread for j in self._jobs.values() if j.thread and j.thread.is_alive()]
            for job in self._jobs.values():
                job.stop_event.set()
        for thread in threads:
            thread.join(timeout=5)
