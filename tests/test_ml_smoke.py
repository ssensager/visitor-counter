"""Smoke-тесты реального ML-счётчика (ml/VisitorCounter).

До слияния ветки `feature/ml-counter` пакета `ml` в репозитории нет (только
`.gitkeep`), поэтому весь файл мягко пропускается через `pytest.importorskip`.
После интеграции эти тесты проверяют контракт из PROJECT_SPEC.md 3.1:
`process_frame`, `reset`, формат `stats`.

Конструктор VisitorCounter загружает YOLOv8n, поэтому если веса или torch
недоступны в окружении, тест помечается skip, а не падает.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable

import pytest

ml = pytest.importorskip("ml", reason="пакет ml/ ещё не слит (ожидается из feature/ml-counter)")


def _resolve_counter_class() -> type | None:
    """Ищем VisitorCounter в ml, ml.counter или ml.processor."""
    candidate = getattr(ml, "VisitorCounter", None)
    if candidate is not None:
        return candidate

    for module_name in ("ml.counter", "ml.processor"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        candidate = getattr(module, "VisitorCounter", None)
        if candidate is not None:
            return candidate
    return None


VisitorCounter = _resolve_counter_class()

pytestmark = pytest.mark.skipif(
    VisitorCounter is None,
    reason="ml.VisitorCounter не найден (проверьте реэкспорт в ml/__init__.py)",
)


@pytest.fixture(scope="module")
def counter() -> Any:
    """Один VisitorCounter на модуль: модель грузится один раз."""

    assert VisitorCounter is not None
    try:
        instance = VisitorCounter(line=((0, 120), (320, 120)))
    except Exception as exc:  # noqa: BLE001 - окружение без весов/torch должно давать skip
        pytest.skip(f"VisitorCounter не инициализируется в этом окружении: {exc}")
    return instance


def test_counter_implements_required_api(counter: Any) -> None:
    for method in ("set_line", "process_frame", "reset"):
        assert callable(getattr(counter, method, None)), f"нет метода {method}"


def test_process_frame_returns_frame_and_stats(counter: Any, frame_factory: Callable[..., Any]) -> None:
    frame = frame_factory(width=640, height=480)

    output, stats = counter.process_frame(frame)

    assert output is not None
    assert hasattr(output, "shape"), "process_frame должен вернуть изображение (np.ndarray)"
    assert output.shape == frame.shape
    assert isinstance(stats, dict)


def test_stats_follow_contract(counter: Any, frame_factory: Callable[..., Any]) -> None:
    _, stats = counter.process_frame(frame_factory(width=640, height=480))

    for key in ("entered", "exited", "current", "people"):
        assert key in stats, f"в stats нет ключа {key}"

    assert isinstance(stats["entered"], int)
    assert isinstance(stats["exited"], int)
    assert isinstance(stats["current"], int)
    assert stats["current"] == stats["entered"] - stats["exited"]
    assert isinstance(stats["people"], list)


def test_people_bbox_is_four_ints(counter: Any, frame_factory: Callable[..., Any]) -> None:
    _, stats = counter.process_frame(frame_factory(width=640, height=480))

    for person in stats["people"]:
        assert set(person) >= {"id", "bbox"}
        assert isinstance(person["id"], int)
        bbox = person["bbox"]
        assert len(bbox) == 4
        assert all(isinstance(value, int) for value in bbox)


def test_blank_frame_gives_zero_counts(counter: Any, frame_factory: Callable[..., Any]) -> None:
    counter.reset()

    _, stats = counter.process_frame(frame_factory(width=640, height=480))

    assert stats["entered"] == 0
    assert stats["exited"] == 0
    assert stats["people"] == []


def test_process_frame_does_not_mutate_input(counter: Any, frame_factory: Callable[..., Any]) -> None:
    frame = frame_factory(width=640, height=480)
    frame_copy = frame.copy()

    counter.process_frame(frame)

    assert (frame == frame_copy).all(), "process_frame обязан рисовать на копии кадра"


def test_reset_clears_counters(counter: Any, frame_factory: Callable[..., Any]) -> None:
    frame = frame_factory(width=640, height=480)
    for _ in range(3):
        counter.process_frame(frame)

    counter.reset()
    _, stats = counter.process_frame(frame)

    assert stats["entered"] == 0
    assert stats["exited"] == 0
    assert stats["current"] == 0


def test_set_line_accepts_points(counter: Any, frame_factory: Callable[..., Any]) -> None:
    counter.set_line((0, 50), (640, 50))

    output, stats = counter.process_frame(frame_factory(width=640, height=480))

    assert output is not None
    assert "entered" in stats
