"""Тесты общих контрактов и MockVisitorCounter.

Эти тесты не требуют torch, ultralytics, OpenCV и FastAPI: они проверяют
`shared/contracts.py` и `shared/mock_counter.py`, поэтому выполняются всегда -
и до слияния тяжёлых модулей, и после него.
"""

from __future__ import annotations

import pytest

from shared.contracts import (
    ALLOWED_VIDEO_EXTENSIONS,
    JOB_STATUSES,
    FrameStats,
    PersonDetection,
    VideoProcessorProtocol,
    VisitorCounterProtocol,
)
from shared.mock_counter import MockVisitorCounter


# ---------------------------------------------------------------------------
# shared/contracts.py
# ---------------------------------------------------------------------------


def test_allowed_video_extensions_match_spec() -> None:
    assert ALLOWED_VIDEO_EXTENSIONS == (".mp4", ".avi")


def test_job_statuses_match_spec() -> None:
    assert JOB_STATUSES == ("uploaded", "processing", "completed", "stopped", "error")
    assert all(isinstance(status, str) for status in JOB_STATUSES)


def test_person_detection_to_dict_coerces_bbox_to_int() -> None:
    person = PersonDetection(id=7, bbox=[10.9, 20.2, 30.5, 40.1])  # type: ignore[list-item]

    assert person.to_dict() == {"id": 7, "bbox": [10, 20, 30, 40]}


def test_frame_stats_defaults_are_zero() -> None:
    stats = FrameStats()

    assert (stats.entered, stats.exited, stats.current) == (0, 0, 0)
    assert stats.people == []
    assert stats.fps is None
    assert stats.frame_index is None
    assert stats.progress is None


def test_frame_stats_to_ml_dict_has_exact_keys() -> None:
    stats = FrameStats(
        entered=15,
        exited=8,
        current=7,
        people=[PersonDetection(id=1, bbox=[120, 80, 210, 350])],
    )

    payload = stats.to_ml_dict()

    assert set(payload) == {"entered", "exited", "current", "people"}
    assert payload["people"] == [{"id": 1, "bbox": [120, 80, 210, 350]}]


def test_frame_stats_to_ml_dict_omits_video_only_fields() -> None:
    stats = FrameStats(entered=1, exited=0, current=1)
    stats.fps = 28.5
    stats.frame_index = 42
    stats.progress = 0.5

    payload = stats.to_ml_dict()

    assert "fps" not in payload
    assert "frame_index" not in payload
    assert "progress" not in payload


def test_frame_stats_to_dict_rounds_optional_fields() -> None:
    stats = FrameStats(entered=15, exited=8, current=7)
    stats.fps = 28.456
    stats.frame_index = 42
    stats.progress = 0.42123

    payload = stats.to_dict()

    assert payload["fps"] == 28.46
    assert payload["frame_index"] == 42
    assert payload["progress"] == 0.4212


def test_mock_satisfies_visitor_counter_protocol() -> None:
    counter = MockVisitorCounter()

    assert isinstance(counter, VisitorCounterProtocol)
    assert not isinstance(counter, VideoProcessorProtocol)


def test_ml_and_video_protocols_are_runtime_checkable() -> None:
    class _VideoLike:
        def process(self, source, stop_event=None):  # noqa: ANN001, ANN201
            return iter(())

    assert isinstance(_VideoLike(), VideoProcessorProtocol)
    assert not isinstance(_VideoLike(), VisitorCounterProtocol)


# ---------------------------------------------------------------------------
# shared/mock_counter.py
# ---------------------------------------------------------------------------


def test_mock_exposes_constructor_arguments() -> None:
    line = ((0, 100), (320, 100))
    counter = MockVisitorCounter(model_path="yolov8n.pt", line=line, conf_threshold=0.5)

    assert counter.model_path == "yolov8n.pt"
    assert counter.line == line
    assert counter.conf_threshold == 0.5


def test_mock_set_line_updates_line() -> None:
    counter = MockVisitorCounter()
    counter.set_line((0, 10), (640, 10))

    assert counter.line == ((0, 10), (640, 10))


def test_mock_first_29_frames_have_no_counts() -> None:
    counter = MockVisitorCounter()

    for _ in range(29):
        _, stats = counter.process_frame(object())

    assert (stats["entered"], stats["exited"], stats["current"]) == (0, 0, 0)


def test_mock_counts_entered_on_every_30th_frame() -> None:
    counter = MockVisitorCounter()
    stats: dict = {}

    for frame_number in range(1, 61):
        _, stats = counter.process_frame(object())
        if frame_number == 30:
            assert (stats["entered"], stats["exited"], stats["current"]) == (1, 0, 1)
        if frame_number == 60:
            # 55-й кадр уже добавил одного вышедшего, поэтому current = 2 - 1.
            assert (stats["entered"], stats["exited"], stats["current"]) == (2, 1, 1)


def test_mock_counts_exited_on_55th_frame() -> None:
    counter = MockVisitorCounter()
    stats: dict = {}

    for _ in range(55):
        _, stats = counter.process_frame(object())

    assert (stats["entered"], stats["exited"], stats["current"]) == (1, 1, 0)


def test_mock_current_is_entered_minus_exited() -> None:
    counter = MockVisitorCounter()

    for _ in range(200):
        _, stats = counter.process_frame(object())
        assert stats["current"] == stats["entered"] - stats["exited"]


def test_mock_reset_clears_counters_and_restarts_schedule() -> None:
    counter = MockVisitorCounter()
    for _ in range(55):
        counter.process_frame(object())

    counter.reset()
    _, stats = counter.process_frame(object())

    assert (stats["entered"], stats["exited"], stats["current"]) == (0, 0, 0)

    for _ in range(29):
        _, stats = counter.process_frame(object())
    assert stats["entered"] == 1


def test_mock_people_bbox_format() -> None:
    counter = MockVisitorCounter()

    _, stats = counter.process_frame(object())

    assert len(stats["people"]) == 1
    person = stats["people"][0]
    assert set(person) == {"id", "bbox"}
    assert isinstance(person["id"], int)
    assert len(person["bbox"]) == 4
    assert all(isinstance(value, int) for value in person["bbox"])
    x1, y1, x2, y2 = person["bbox"]
    assert x2 > x1 and y2 > y1


def test_mock_returns_new_frame_object(np) -> None:
    counter = MockVisitorCounter()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    output, _ = counter.process_frame(frame)

    assert output is not frame
    assert output.shape == frame.shape
    assert int(frame.sum()) == 0, "исходный кадр не должен изменяться"


def test_mock_draws_overlay_when_cv2_available(np) -> None:
    cv2 = pytest.importorskip("cv2", reason="OpenCV не установлен")
    assert cv2 is not None  # используем импорт, чтобы skip сработал без cv2

    counter = MockVisitorCounter()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    output, stats = counter.process_frame(frame)

    assert int(output.sum()) > 0, "на кадр должны быть нанесены линия и рамка"
    assert stats["people"][0]["bbox"] == [120, 84, 210, 224]


def test_mock_works_with_non_array_frame() -> None:
    counter = MockVisitorCounter()

    output, stats = counter.process_frame({"pixels": b"raw"})

    assert output == {"pixels": b"raw"}
    assert stats["entered"] == 0


def test_mock_default_line_is_center_of_frame(np) -> None:
    counter = MockVisitorCounter()
    frame = np.zeros((200, 400, 3), dtype=np.uint8)
    pytest.importorskip("cv2", reason="OpenCV не установлен")

    output, _ = counter.process_frame(frame)

    # Линия по умолчанию проходит по y = height // 2 = 100: пиксели строки 100
    # должны измениться, а строка 10 - остаться чёрной.
    assert int(output[100, :, :].sum()) > 0
    assert int(output[10, :, :].sum()) == 0


def test_mock_is_deterministic() -> None:
    """Одинаковая последовательность кадров даёт одинаковую статистику."""
    first, second = MockVisitorCounter(), MockVisitorCounter()

    for _ in range(90):
        _, stats_first = first.process_frame(object())
        _, stats_second = second.process_frame(object())

    assert stats_first == stats_second


def test_mock_conf_and_line_are_optional() -> None:
    counter = MockVisitorCounter(line=None)
    counter.set_line((0, 0), (1, 1))
    _, stats = counter.process_frame(object())

    assert stats["entered"] == 0
