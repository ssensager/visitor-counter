"""Общие фикстуры и настройка путей для тестов visitor-counter.

Файл намеренно не импортирует тяжёлые зависимости на уровне модуля:
numpy и OpenCV подхватываются через фикстуры, чтобы `test_contracts.py`
проходил даже в «голом» окружении без ML-библиотек.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
for _path in (REPO_ROOT, TESTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def pytest_configure(config: "pytest.Config") -> None:
    """Регистрируем маркеры, чтобы pytest не ругался на неизвестные имена."""
    config.addinivalue_line("markers", "requires_cv2: тест требует установленный OpenCV (cv2)")
    config.addinivalue_line("markers", "requires_numpy: тест требует установленный numpy")
    config.addinivalue_line("markers", "requires_torch: тест требует torch/ultralytics")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Корень репозитория (относительно него лежат shared/, ml/, backend/)."""
    return REPO_ROOT


@pytest.fixture()
def np():
    """numpy или мягкий skip, если он не установлен."""
    return pytest.importorskip("numpy", reason="numpy не установлен")


@pytest.fixture()
def cv2():
    """OpenCV или мягкий skip."""
    return pytest.importorskip("cv2", reason="OpenCV не установлен (pip install opencv-python)")


@pytest.fixture()
def frame_factory(np) -> Callable[..., "object"]:
    """Фабрика пустых BGR-кадров нужного размера."""

    def _make(width: int = 320, height: int = 240):
        return np.zeros((height, width, 3), dtype=np.uint8)

    return _make


@pytest.fixture()
def video_factory(cv2, np, tmp_path: Path) -> Callable[..., Path]:
    """Фабрика коротких синтетических видео (MJPG/AVI) для тестов и CLI."""

    def _make(
        name: str = "clip.avi",
        frames: int = 12,
        width: int = 320,
        height: int = 240,
        fps: float = 10.0,
    ) -> Path:
        path = tmp_path / name
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
        if not writer.isOpened():
            pytest.skip("cv2.VideoWriter не смог открыть MJPG-файл в этом окружении")
        try:
            for index in range(frames):
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:, :, 0] = (index * 15) % 256
                writer.write(frame)
        finally:
            writer.release()
        if not path.exists() or path.stat().st_size == 0:
            pytest.skip("синтетическое видео не записалось (кодек MJPG недоступен)")
        return path

    return _make
