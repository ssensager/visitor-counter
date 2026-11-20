"""Тесты утилиты оценки точности (evaluate_accuracy.py) и сборки таблицы.

Проверяются:
- формула ошибки из PROJECT_SPEC.md 5 (включая случай "факт = 0");
- разбор виртуальной линии;
- CLI целиком на синтетическом видео в режиме --mock;
- markdown-таблица для отчёта и заготовка на 3 видео.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest

from benchmark_accuracy import build_markdown_table, load_manifest
from evaluate_accuracy import (
    EXIT_OK,
    EXIT_THRESHOLD,
    EXIT_USAGE,
    EvaluationError,
    VideoEvaluation,
    _load_visitor_counter_class,
    compute_metrics,
    format_report,
    main,
    parse_line,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# compute_metrics: формула ошибки
# ---------------------------------------------------------------------------


def test_exact_match_has_zero_error() -> None:
    metrics = compute_metrics(actual=10, auto=10)

    assert metrics.abs_error == 0
    assert metrics.error_pct == 0.0
    assert metrics.is_within(5.0)


def test_overcount_error_percent() -> None:
    metrics = compute_metrics(actual=10, auto=12)

    assert metrics.abs_error == 2
    assert metrics.error_pct == pytest.approx(20.0)
    assert not metrics.is_within(5.0)


def test_undercount_error_percent() -> None:
    metrics = compute_metrics(actual=20, auto=19)

    assert metrics.abs_error == 1
    assert metrics.error_pct == pytest.approx(5.0)
    assert metrics.is_within(5.0), "ровно 5% должно попадать в ориентир"


def test_actual_zero_reports_only_absolute_error() -> None:
    metrics = compute_metrics(actual=0, auto=0)

    assert metrics.error_pct is None
    assert metrics.abs_error == 0
    assert metrics.is_within(5.0)


def test_actual_zero_with_false_positives_fails() -> None:
    metrics = compute_metrics(actual=0, auto=3)

    assert metrics.error_pct is None
    assert metrics.abs_error == 3
    assert not metrics.is_within(5.0)


def test_tolerance_boundary() -> None:
    assert compute_metrics(actual=100, auto=105).is_within(5.0)
    assert not compute_metrics(actual=100, auto=106).is_within(5.0)


def test_negative_actual_is_rejected() -> None:
    with pytest.raises(ValueError):
        compute_metrics(actual=-1, auto=0)


def test_metrics_to_dict_rounds_percent() -> None:
    payload = compute_metrics(actual=3, auto=4).to_dict()

    assert payload == {"actual": 3, "auto": 4, "abs_error": 1, "error_pct": 33.3333}


# ---------------------------------------------------------------------------
# Разбор линии
# ---------------------------------------------------------------------------


def test_parse_line_accepts_comma_format() -> None:
    assert parse_line("0,10,640,10") == ((0, 10), (640, 10))


def test_parse_line_accepts_spaces_and_semicolon() -> None:
    assert parse_line("0; 10; 640; 10") == ((0, 10), (640, 10))


@pytest.mark.parametrize("text", ["", "1,2,3", "0,0,0,0", "a,b,c,d", "0,10,640"])
def test_parse_line_rejects_bad_input(text: str) -> None:
    with pytest.raises(ValueError):
        parse_line(text)


# ---------------------------------------------------------------------------
# Отчёт и таблица
# ---------------------------------------------------------------------------


def _make_result(actual_in: int, auto_in: int, actual_out: int, auto_out: int) -> VideoEvaluation:
    return VideoEvaluation(
        video="storage/test_videos/simple.avi",
        mode="mock",
        frames=30,
        elapsed_s=0.5,
        fps=60.0,
        video_fps=10.0,
        entered=compute_metrics(actual_in, auto_in),
        exited=compute_metrics(actual_out, auto_out),
        tolerance=5.0,
        label="простое",
    )


def test_format_report_contains_metrics() -> None:
    report = format_report(_make_result(actual_in=10, auto_in=9, actual_out=0, auto_out=0))

    assert "Вошло" in report and "Вышло" in report
    assert "10.00" in report, "ошибка 1/10 = 10%"
    assert "n/a (факт = 0)" in report
    assert "FAIL" in report
    assert "FPS" in report


def test_markdown_table_template_has_three_rows() -> None:
    table = build_markdown_table([], template_only=True)

    rows = [line for line in table.splitlines() if line.startswith("| ")]
    assert len(rows) == 3 + 2, "шапка + выравнивание + 3 строки"
    for complexity in ("простое", "среднее", "сложное"):
        assert complexity in table
    assert "<= 5%" in table


def test_markdown_table_with_results() -> None:
    results = [
        _make_result(10, 10, 9, 9),
        _make_result(12, 15, 11, 11),
    ]

    table = build_markdown_table(results)

    assert "PASS" in table
    assert "FAIL" in table
    assert "0.00" in table


def test_markdown_table_marks_errors() -> None:
    table = build_markdown_table([None], errors=["видео не найдено"])

    assert "FAIL" in table
    assert "видео не найдено" in table


# ---------------------------------------------------------------------------
# Манифест
# ---------------------------------------------------------------------------


def test_load_manifest_supports_dict_and_list(tmp_path: Path) -> None:
    dict_manifest = tmp_path / "dict.json"
    dict_manifest.write_text(json.dumps({"videos": [{"path": "a.mp4"}]}), encoding="utf-8")
    list_manifest = tmp_path / "list.json"
    list_manifest.write_text(json.dumps([{"path": "a.mp4"}]), encoding="utf-8")

    assert load_manifest(dict_manifest)[0]["path"] == "a.mp4"
    assert load_manifest(list_manifest)[0]["path"] == "a.mp4"


def test_load_manifest_supports_bom(tmp_path: Path) -> None:
    """Блокнот Windows сохраняет JSON с BOM - манифест должен читаться."""
    manifest = tmp_path / "bom.json"
    manifest.write_text(json.dumps({"videos": [{"path": "a.mp4"}]}), encoding="utf-8-sig")

    assert load_manifest(manifest)[0]["path"] == "a.mp4"


def test_load_manifest_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(EvaluationError):
        load_manifest(tmp_path / "nope.json")


def test_load_manifest_rejects_empty_list(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"videos": []}), encoding="utf-8")

    with pytest.raises(EvaluationError):
        load_manifest(empty)


# ---------------------------------------------------------------------------
# CLI на синтетическом видео (режим --mock)
# ---------------------------------------------------------------------------


def test_cli_mock_mode_end_to_end(
    video_factory: Callable[..., Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    video = video_factory(name="cli.avi", frames=12)
    json_path = tmp_path / "result.json"

    exit_code = main(
        [
            str(video),
            "--actual-in",
            "0",
            "--actual-out",
            "0",
            "--mock",
            "--json",
            str(json_path),
        ]
    )

    assert exit_code == EXIT_OK
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "mock"
    assert payload["frames"] == 12
    assert payload["video"] == str(video)
    assert payload["entered"] == {"actual": 0, "auto": 0, "abs_error": 0, "error_pct": None}
    assert payload["passed"] is True
    assert payload["fps"] > 0
    assert "Видео" in capsys.readouterr().out


def test_cli_fail_over_returns_exit_code_3(video_factory: Callable[..., Path]) -> None:
    video = video_factory(name="fail.avi", frames=12)

    exit_code = main(
        [str(video), "--actual-in", "5", "--actual-out", "0", "--mock", "--fail-over", "--quiet"]
    )

    assert exit_code == EXIT_THRESHOLD


def test_cli_without_fail_over_returns_zero(video_factory: Callable[..., Path]) -> None:
    video = video_factory(name="ok.avi", frames=12)

    exit_code = main([str(video), "--actual-in", "5", "--actual-out", "0", "--mock", "--quiet"])

    assert exit_code == EXIT_OK


def test_cli_missing_video_returns_usage_error(tmp_path: Path) -> None:
    exit_code = main(
        [str(tmp_path / "absent.mp4"), "--actual-in", "1", "--actual-out", "1", "--mock", "--quiet"]
    )

    assert exit_code == EXIT_USAGE


def test_cli_rejects_negative_actuals(video_factory: Callable[..., Path]) -> None:
    video = video_factory(name="neg.avi", frames=3)

    with pytest.raises(SystemExit) as excinfo:
        main([str(video), "--actual-in", "-1", "--actual-out", "0", "--mock"])

    assert excinfo.value.code == EXIT_USAGE


def test_cli_max_frames_limits_processing(video_factory: Callable[..., Path], tmp_path: Path) -> None:
    video = video_factory(name="limit.avi", frames=20)
    json_path = tmp_path / "limit.json"

    exit_code = main(
        [
            str(video),
            "--actual-in",
            "0",
            "--actual-out",
            "0",
            "--mock",
            "--max-frames",
            "5",
            "--json",
            str(json_path),
            "--quiet",
        ]
    )

    assert exit_code == EXIT_OK
    assert json.loads(json_path.read_text(encoding="utf-8"))["frames"] == 5


@pytest.mark.skipif(
    _load_visitor_counter_class() is not None,
    reason="пакет ml/ уже слит: ветку без ML-модуля проверять не нужно",
)
def test_cli_real_mode_without_ml_explains_how_to_use_mock(video_factory: Callable[..., Path]) -> None:
    video = video_factory(name="real.avi", frames=3)

    exit_code = main([str(video), "--actual-in", "1", "--actual-out", "1", "--quiet"])

    assert exit_code == 4, "без ml/ ожидаем код 4 (нет зависимости)"
    assert _load_visitor_counter_class() is None


# ---------------------------------------------------------------------------
# Запуск как отдельный процесс (проверяем __main__ и sys.path)
# ---------------------------------------------------------------------------


def test_script_runs_as_subprocess_with_json_stdout(video_factory: Callable[..., Path]) -> None:
    video = video_factory(name="subprocess.avi", frames=12)

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tests" / "evaluate_accuracy.py"),
            str(video),
            "--actual-in",
            "0",
            "--actual-out",
            "0",
            "--mock",
            "--json",
            "-",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["frames"] == 12
    assert payload["mode"] == "mock"


def test_benchmark_table_template_via_subprocess() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tests" / "benchmark_accuracy.py"), "--table-template"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )

    assert completed.returncode == 0, completed.stderr
    assert "простое" in completed.stdout
    assert "среднее" in completed.stdout
    assert "сложное" in completed.stdout
