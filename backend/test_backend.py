"""Backend-owned contract/integration tests; no changes to the team's tests/ folder."""

import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.main import create_app
from backend.services.job_manager import JobError, JobManager
from backend.services.video_service import VideoService, exported_class
from shared.mock_counter import MockVisitorCounter


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VISITOR_USE_MOCK", "1")
    with TestClient(create_app(tmp_path / "uploads", tmp_path / "frontend")) as instance:
        yield instance


def make_video(tmp_path, frames=8, extension=".mp4"):
    path = tmp_path / f"source{extension}"
    codec = "mp4v" if extension == ".mp4" else "MJPG"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), 25, (320, 240))
    assert writer.isOpened()
    try:
        for index in range(frames):
            writer.write(np.full((240, 320, 3), index % 255, dtype=np.uint8))
    finally:
        writer.release()
    return path.read_bytes()


def upload(client, data=b"not a video", filename="demo.mp4"):
    response = client.post("/api/video/upload", files={"file": (filename, data)})
    assert response.status_code == 200, response.text
    return response.json()["job_id"]


def wait_stats(client, job_id, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = client.get(f"/api/stats/{job_id}").json()
        if predicate(result):
            return result
        time.sleep(0.01)
    pytest.fail(f"Timed out waiting for stats: {result}")


def test_health_and_empty_frontend(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200


def test_static_frontend_does_not_shadow_api(tmp_path):
    frontend = tmp_path / "frontend"
    (frontend / "css").mkdir(parents=True)
    (frontend / "index.html").write_text("<h1>Dashboard</h1>")
    (frontend / "css/style.css").write_text("body { color: red; }")
    with TestClient(create_app(tmp_path / "uploads", frontend)) as client:
        assert "Dashboard" in client.get("/").text
        assert client.get("/css/style.css").status_code == 200
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/stats/missing").status_code == 404


def test_upload_validation_and_storage(client):
    for filename, data, status in [("x.txt", b"hello", 415), ("x.mp4", b"", 400)]:
        response = client.post("/api/video/upload", files={"file": (filename, data)})
        assert response.status_code == status
        assert "detail" in response.json()
    job_id = upload(client, b"content", "../../outside.MP4")
    directory = client.app.state.manager.upload_dir
    assert (directory / f"{job_id}.mp4").read_bytes() == b"content"
    assert len(list(directory.iterdir())) == 1
    assert client.get(f"/api/stats/{job_id}").json() == {
        "job_id": job_id, "entered": 0, "exited": 0, "current": 0,
        "fps": 0.0, "progress": 0.0, "status": "uploaded", "error": None,
    }


def test_size_limit_removes_partial_file(client):
    manager = client.app.state.manager
    manager.max_upload_bytes = 3
    response = client.post("/api/video/upload", files={"file": ("x.mp4", b"1234")})
    assert response.status_code == 413
    assert list(manager.upload_dir.iterdir()) == []


@pytest.mark.parametrize("method,path", [
    ("get", "/api/stats/missing"), ("get", "/api/video/stream/missing"),
    ("post", "/api/video/start/missing"), ("post", "/api/video/stop/missing"),
])
def test_unknown_job(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 404
    assert response.json() == {"detail": "Задача не найдена"}


def test_unstarted_stop_and_stream(client):
    job_id = upload(client)
    assert client.post(f"/api/video/stop/{job_id}").status_code == 409
    assert client.get(f"/api/video/stream/{job_id}").status_code == 409


@pytest.mark.parametrize("line", [[[0, 0], [0, 0]], [[-1, 0], [10, 10]],
                                 [[0, 0]], [[0.5, 0], [10, 10]]])
def test_line_validation(client, line):
    job_id = upload(client)
    assert client.post(f"/api/video/start/{job_id}", json={"line": line}).status_code == 422
    assert client.get(f"/api/stats/{job_id}").json()["status"] == "uploaded"


def test_mock_stop_restart_and_single_active(client, tmp_path):
    data = make_video(tmp_path, frames=100)
    first, second = upload(client, data), upload(client, data)
    assert client.post(f"/api/video/start/{first}", json={"line": [[0, 30], [320, 30]]}).status_code == 200
    result = wait_stats(client, first, lambda s: s["entered"] > 0)
    assert result["current"] == result["entered"] - result["exited"]
    assert result["fps"] > 0
    for job_id in [first, second]:
        assert client.post(f"/api/video/start/{job_id}").status_code == 409
    assert client.post(f"/api/video/stop/{first}").json()["status"] == "stopped"
    assert client.post(f"/api/video/stop/{first}").status_code == 200
    assert client.post(f"/api/video/start/{first}").status_code == 200
    restarted = wait_stats(client, first, lambda s: s["progress"] > 0)
    assert restarted["entered"] == restarted["exited"] == 0
    assert client.app.state.video_service._counter.line == ((0, 120), (320, 120))
    assert client.post(f"/api/video/stop/{first}").status_code == 200
    assert client.post(f"/api/video/start/{second}").status_code == 200
    assert client.post(f"/api/video/stop/{second}").status_code == 200


@pytest.mark.parametrize("extension", [".mp4", ".avi"])
def test_completion_websocket_and_mjpeg(client, tmp_path, extension):
    job_id = upload(client, make_video(tmp_path, extension=extension), "demo" + extension)
    assert client.post(f"/api/video/start/{job_id}").status_code == 200
    messages = []
    with client.websocket_connect(f"/ws/stats/{job_id}") as ws:
        while True:
            value = ws.receive_json()
            messages.append(value)
            if value["status"] == "completed":
                with pytest.raises(WebSocketDisconnect) as closed:
                    ws.receive_json()
                assert closed.value.code == 1000
                break
    assert messages[-1]["progress"] == 1.0
    assert messages[-1]["error"] is None
    response = client.get(f"/api/video/stream/{job_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "multipart/x-mixed-replace; boundary=frame"
    assert b"Content-Type: image/jpeg\r\n" in response.content
    jpeg = response.content.split(b"\r\n\r\n", 1)[1].split(b"\r\n--frame", 1)[0]
    assert cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR).shape == (240, 320, 3)


def test_stream_while_processing(client, tmp_path):
    job_id = upload(client, make_video(tmp_path, frames=5))
    client.post(f"/api/video/start/{job_id}")
    response = client.get(f"/api/video/stream/{job_id}")
    assert b"Content-Type: image/jpeg" in response.content
    assert response.content.endswith(b"--frame--\r\n")
    assert client.get(f"/api/stats/{job_id}").json()["status"] == "completed"


def test_websocket_disconnect_keeps_processing(client, tmp_path):
    job_id = upload(client, make_video(tmp_path, frames=100))
    client.post(f"/api/video/start/{job_id}")
    with client.websocket_connect(f"/ws/stats/{job_id}") as ws:
        assert ws.receive_json()["status"] == "processing"
    assert client.get(f"/api/stats/{job_id}").json()["status"] == "processing"
    assert client.post(f"/api/video/stop/{job_id}").status_code == 200


def test_unknown_websocket(client):
    with client.websocket_connect("/ws/stats/missing") as ws:
        assert ws.receive_json() == {"detail": "Задача не найдена"}
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 1008


def test_corrupt_video_errors_and_releases_slot(client):
    first, second = upload(client), upload(client)
    client.post(f"/api/video/start/{first}")
    result = wait_stats(client, first, lambda s: s["status"] == "error")
    assert result["error"]
    assert client.post(f"/api/video/start/{second}").status_code == 200
    wait_stats(client, second, lambda s: s["status"] == "error")


def test_atomic_admission_and_stop_keeps_slot(tmp_path):
    manager = JobManager(tmp_path)
    ids = [manager.upload("x.mp4", io.BytesIO(b"x")).job_id for _ in range(2)]
    release = threading.Event()
    barrier = threading.Barrier(2)

    def worker(job, line):
        release.wait(5)
        manager.finish(job.job_id)

    def start(job_id):
        barrier.wait()
        try:
            manager.start(job_id, None, worker)
            return 200, job_id
        except JobError as exc:
            return exc.status_code, job_id

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(start, ids))
        assert sorted(status for status, _ in results) == [200, 409]
        active = next(job_id for status, job_id in results if status == 200)
        thread = manager.request_stop(active)
        with pytest.raises(JobError) as conflict:
            manager.start(ids[0], None, worker)
        assert conflict.value.status_code == 409
        release.set()
        thread.join(2)
        assert manager.snapshot(active)[0].status == "stopped"
    finally:
        release.set()
        manager.shutdown()


def test_shutdown_stops_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("VISITOR_USE_MOCK", "1")
    app = create_app(tmp_path / "uploads", tmp_path / "frontend")
    with TestClient(app) as client:
        job_id = upload(client, make_video(tmp_path, frames=100))
        client.post(f"/api/video/start/{job_id}")
        wait_stats(client, job_id, lambda s: s["progress"] > 0)
    assert app.state.manager.snapshot(job_id)[0].status == "stopped"


def test_shutdown_after_lifespan_exception(tmp_path):
    import asyncio

    app = create_app(tmp_path / "uploads", tmp_path / "frontend")

    async def run():
        with pytest.raises(RuntimeError, match="lifespan failure"):
            async with app.router.lifespan_context(app):
                raise RuntimeError("lifespan failure")

    asyncio.run(run())
    with pytest.raises(JobError) as closed:
        app.state.manager.upload("test.mp4", io.BytesIO(b"test"))
    assert closed.value.status_code == 503
    assert list((tmp_path / "uploads").iterdir()) == []


def test_real_exports_selected_and_counter_reused(tmp_path, monkeypatch):
    monkeypatch.delenv("VISITOR_USE_MOCK", raising=False)
    calls = []

    class Counter(MockVisitorCounter):
        def __init__(self):
            calls.append("counter")
            super().__init__()

    class Processor:
        def __init__(self, counter):
            self.counter = counter

        def process(self, source, stop_event=None):
            calls.append("process")
            frame, stats = self.counter.process_frame(np.zeros((240, 320, 3), dtype=np.uint8))
            yield frame, dict(stats, fps=12, progress=1.0)

    monkeypatch.setattr("backend.services.video_service.importlib.import_module",
                        lambda name: SimpleNamespace(**{"VisitorCounter" if name == "ml" else "VideoProcessor":
                                                        Counter if name == "ml" else Processor}))
    with TestClient(create_app(tmp_path / "uploads", tmp_path / "frontend")) as client:
        job_id = upload(client, make_video(tmp_path))
        for _ in range(2):
            client.post(f"/api/video/start/{job_id}")
            wait_stats(client, job_id, lambda s: s["status"] == "completed")
    assert calls == ["counter", "process", "process"]


def test_missing_exports_use_mock(tmp_path, monkeypatch):
    monkeypatch.delenv("VISITOR_USE_MOCK", raising=False)
    monkeypatch.setattr("backend.services.video_service.importlib.import_module", lambda name: SimpleNamespace())
    service = VideoService(JobManager(tmp_path))
    service._processor(None)
    assert isinstance(service._counter, MockVisitorCounter)


def test_internal_import_failure_is_not_hidden(monkeypatch):
    def broken(name):
        raise ModuleNotFoundError("No module named torch", name="torch")
    monkeypatch.setattr("backend.services.video_service.importlib.import_module", broken)
    with pytest.raises(ModuleNotFoundError):
        exported_class("ml", "VisitorCounter")
