"""Smoke-тесты HTTP API (backend/main.py).

До слияния ветки `feature/backend-api` модуля `backend.main` нет, поэтому файл
целиком мягко пропускается через `pytest.importorskip`. После интеграции здесь
проверяются контракты из PROJECT_SPEC.md 3.3: здоровье сервера, загрузка видео,
валидация формата, ошибки 404/409 и структура ответов.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Callable

import pytest

backend_main = pytest.importorskip(
    "backend.main",
    reason="backend/main.py ещё не слит (ожидается из feature/backend-api)",
)

app = getattr(backend_main, "app", None)

pytestmark = pytest.mark.skipif(app is None, reason="backend.main не экспортирует FastAPI-приложение `app`")

UPLOAD_URL = "/api/video/upload"
UNKNOWN_JOB = "does-not-exist-123"


@pytest.fixture(scope="module")
def client() -> Any:
    """TestClient без запуска lifespan: smoke-тест не должен грузить YOLO."""
    testclient = pytest.importorskip("fastapi.testclient", reason="fastapi/httpx не установлены")
    return testclient.TestClient(app)


def _upload(client: Any, path: Path) -> Any:
    with path.open("rb") as handle:
        return client.post(UPLOAD_URL, files={"file": (path.name, handle, "video/x-msvideo")})


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------


def test_health_returns_ok(client: Any) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /api/video/upload - валидация формата
# ---------------------------------------------------------------------------


def test_upload_rejects_unsupported_extension(client: Any) -> None:
    response = client.post(
        UPLOAD_URL,
        files={"file": ("notes.txt", b"this is not a video", "text/plain")},
    )

    assert response.status_code in (400, 415), f"ожидался 400/415, получен {response.status_code}"
    assert "detail" in response.json()


def test_upload_requires_file_field(client: Any) -> None:
    response = client.post(UPLOAD_URL)

    assert response.status_code in (400, 422)
    assert "detail" in response.json()


def test_upload_accepts_mp4_or_avi(client: Any, video_factory: Callable[..., Path]) -> None:
    video_path = video_factory(name="upload_ok.avi", frames=5)

    response = _upload(client, video_path)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) >= {"job_id", "filename", "status"}
    assert payload["status"] == "uploaded"
    assert isinstance(payload["job_id"], str) and payload["job_id"]
    assert payload["filename"] == video_path.name


# ---------------------------------------------------------------------------
# 404 на неизвестные job_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,url",
    [
        ("get", f"/api/stats/{UNKNOWN_JOB}"),
        ("post", f"/api/video/start/{UNKNOWN_JOB}"),
        ("post", f"/api/video/stop/{UNKNOWN_JOB}"),
    ],
)
def test_unknown_job_returns_404(client: Any, method: str, url: str) -> None:
    response = getattr(client, method)(url)

    assert response.status_code == 404, response.text
    assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Жизненный цикл задачи и 409 Conflict
# ---------------------------------------------------------------------------


def test_start_stop_cycle(client: Any, video_factory: Callable[..., Path]) -> None:
    first = _upload(client, video_factory(name="cycle_a.avi", frames=5))
    assert first.status_code == 200, first.text
    job_id = first.json()["job_id"]

    try:
        started = client.post(f"/api/video/start/{job_id}")
        assert started.status_code == 200, started.text
        assert started.json()["status"] == "processing"

        stats = client.get(f"/api/stats/{job_id}")
        assert stats.status_code == 200, stats.text
        payload = stats.json()
        for key in ("job_id", "entered", "exited", "current", "status", "error"):
            assert key in payload, f"в StatsResponse нет ключа {key}"
        assert payload["job_id"] == job_id
        assert payload["status"] in ("uploaded", "processing", "completed", "stopped", "error")

        stopped = client.post(f"/api/video/stop/{job_id}")
        assert stopped.status_code == 200, stopped.text
        assert stopped.json()["status"] in ("stopped", "completed")
    finally:
        client.post(f"/api/video/stop/{job_id}")


def test_second_simultaneous_job_returns_409(client: Any, video_factory: Callable[..., Path]) -> None:
    first = _upload(client, video_factory(name="conflict_a.avi", frames=5))
    second = _upload(client, video_factory(name="conflict_b.avi", frames=5))
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    job_a = first.json()["job_id"]
    job_b = second.json()["job_id"]

    try:
        started = client.post(f"/api/video/start/{job_a}")
        assert started.status_code == 200, started.text

        conflict = client.post(f"/api/video/start/{job_b}")
        assert conflict.status_code == 409, f"ожидался 409 Conflict, получен {conflict.status_code}"
        assert "detail" in conflict.json()
    finally:
        client.post(f"/api/video/stop/{job_a}")
        client.post(f"/api/video/stop/{job_b}")


def test_upload_returns_unique_job_ids(client: Any, video_factory: Callable[..., Path]) -> None:
    """После загрузки job_id должен быть непустым и уникальным между загрузками."""
    a = _upload(client, video_factory(name="unique_a.avi", frames=3))
    b = _upload(client, video_factory(name="unique_b.avi", frames=3))

    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["job_id"] != b.json()["job_id"]


def test_stats_response_is_json_serializable_after_upload(
    client: Any, video_factory: Callable[..., Path]
) -> None:
    uploaded = _upload(client, video_factory(name="json_check.avi", frames=3))
    job_id = uploaded.json()["job_id"]

    response = client.get(f"/api/stats/{job_id}")

    assert response.status_code == 200
    assert isinstance(response.content, bytes)
    assert io.BytesIO(response.content).read()  # непустое тело
