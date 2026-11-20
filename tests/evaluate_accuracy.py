#!/usr/bin/env python
"""CLI-утилита оценки точности подсчёта посетителей (visitor-counter).

Прогоняет видеофайл через VisitorCounter (YOLOv8n + ByteTrack) или через
MockVisitorCounter (флаг --mock), сравнивает автоматический подсчёт с фактом
и считает ошибку по формуле из PROJECT_SPEC.md (раздел 5):

    Ошибка (%) = |Авто - Факт| / Факт * 100%

Если факт равен 0, процент не считается (деление на ноль) - выводится только
абсолютная ошибка |Авто - Факт|.

Примеры запуска (из корня репозитория):

    # Реальный счётчик на реальном видео
    python tests/evaluate_accuracy.py storage/test_videos/simple.mp4 \\
        --actual-in 10 --actual-out 9

    # Проверка самого скрипта без YOLO (mock-счётчик)
    python tests/evaluate_accuracy.py storage/test_videos/simple.mp4 \\
        --actual-in 10 --actual-out 9 --mock

    # Машиночитаемый результат для отчёта/CI + ненулевой код при провале
    python tests/evaluate_accuracy.py video.mp4 --actual-in 12 --actual-out 11 \\
        --json reports/accuracy_simple.json --fail-over

Коды возврата:
    0 - видео обработано (и уложилось в порог, либо --fail-over не указан)
    2 - ошибка аргументов/файла/видео
    3 - ошибка превысила порог tolerance (только с флагом --fail-over)
    4 - нет зависимостей (OpenCV) или не удалось создать счётчик
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

DEFAULT_TOLERANCE = 5.0

# Скрипт запускают и как `python tests/evaluate_accuracy.py`, поэтому корень
# репозитория (для `import shared` / `import ml`) добавляем в sys.path сами.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_THRESHOLD = 3
EXIT_DEPENDENCY = 4


class EvaluationError(RuntimeError):
    """Ошибка оценки: нет зависимостей, видео не открывается, счётчик не создан."""

    def __init__(self, message: str, code: int = EXIT_USAGE) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Метрики
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CountMetrics:
    """Сравнение автоматического и фактического числа людей."""

    actual: int
    auto: int
    abs_error: int
    error_pct: float | None

    def is_within(self, tolerance: float) -> bool:
        """Уложились ли в порог. При факте 0 - только абсолютная ошибка."""
        if self.actual == 0:
            return self.abs_error == 0
        return self.error_pct is not None and self.error_pct <= tolerance

    def to_dict(self) -> dict[str, Any]:
        return {
            "actual": self.actual,
            "auto": self.auto,
            "abs_error": self.abs_error,
            "error_pct": None if self.error_pct is None else round(self.error_pct, 4),
        }

    def as_row(self, label: str) -> str:
        pct = "n/a (факт = 0)" if self.error_pct is None else f"{self.error_pct:.2f}"
        return f"{label:<12} {self.actual:>6} {self.auto:>6} {self.abs_error:>12} {pct:>14}"


def compute_metrics(actual: int, auto: int) -> CountMetrics:
    """Считает абсолютную и относительную ошибку по формуле из спецификации."""
    if actual < 0:
        raise ValueError("Фактическое число посетителей не может быть отрицательным")

    abs_error = abs(auto - actual)
    if actual == 0:
        return CountMetrics(actual=actual, auto=auto, abs_error=abs_error, error_pct=None)

    return CountMetrics(
        actual=actual,
        auto=auto,
        abs_error=abs_error,
        error_pct=abs_error / actual * 100.0,
    )


@dataclass
class VideoEvaluation:
    """Результат прогона одного видео."""

    video: str
    mode: str
    frames: int
    elapsed_s: float
    fps: float
    video_fps: float | None
    entered: CountMetrics
    exited: CountMetrics
    tolerance: float
    label: str | None = None
    model: str | None = None

    @property
    def passed(self) -> bool:
        return self.entered.is_within(self.tolerance) and self.exited.is_within(self.tolerance)

    def to_dict(self) -> dict[str, Any]:
        return {
            "video": self.video,
            "label": self.label,
            "mode": self.mode,
            "model": self.model,
            "frames": self.frames,
            "elapsed_s": round(self.elapsed_s, 4),
            "fps": round(self.fps, 2),
            "video_fps": None if self.video_fps is None else round(self.video_fps, 2),
            "tolerance_pct": self.tolerance,
            "passed": self.passed,
            "entered": self.entered.to_dict(),
            "exited": self.exited.to_dict(),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


# ---------------------------------------------------------------------------
# Счётчики
# ---------------------------------------------------------------------------


def _load_visitor_counter_class() -> type | None:
    """Ищет VisitorCounter в ml/, ml.counter или ml.processor (до слияния - None)."""
    try:
        module = importlib.import_module("ml")
    except ImportError:
        return None

    candidate = getattr(module, "VisitorCounter", None)
    if candidate is not None:
        return candidate

    for module_name in ("ml.counter", "ml.processor"):
        try:
            submodule = importlib.import_module(module_name)
        except ImportError:
            continue
        candidate = getattr(submodule, "VisitorCounter", None)
        if candidate is not None:
            return candidate
    return None


def parse_line(text: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Разбирает строку "x1,y1,x2,y2" в пару точек виртуальной линии."""
    parts = [chunk.strip() for chunk in text.replace(";", ",").split(",")]
    if len(parts) != 4 or any(not part for part in parts):
        raise ValueError(f"Ожидался формат x1,y1,x2,y2, получено: {text!r}")
    try:
        x1, y1, x2, y2 = (int(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"Координаты линии должны быть целыми числами: {text!r}") from exc
    if (x1, y1) == (x2, y2):
        raise ValueError("Точки линии не должны совпадать")
    return (x1, y1), (x2, y2)


def build_counter(
    *,
    mock: bool = False,
    model: str | None = None,
    conf: float = 0.35,
    line: tuple[tuple[int, int], tuple[int, int]] | None = None,
) -> tuple[Any, str]:
    """Создаёт счётчик и возвращает (счётчик, режим: "mock"/"real")."""
    if mock:
        from shared.mock_counter import MockVisitorCounter

        return MockVisitorCounter(model_path=model, line=line, conf_threshold=conf), "mock"

    counter_class = _load_visitor_counter_class()
    if counter_class is None:
        raise EvaluationError(
            "Реальный VisitorCounter недоступен: пакет ml/ не слит или не импортируется. "
            "Для проверки скрипта используйте --mock.",
            code=EXIT_DEPENDENCY,
        )

    try:
        counter = counter_class(model_path=model, line=line, conf_threshold=conf)
    except Exception as exc:  # noqa: BLE001 - причину показываем пользователю
        raise EvaluationError(f"Не удалось создать VisitorCounter: {exc}", code=EXIT_DEPENDENCY) from exc

    return counter, "real"


# ---------------------------------------------------------------------------
# Прогон видео
# ---------------------------------------------------------------------------


def evaluate_video(
    video_path: str | Path,
    counter: Any,
    *,
    actual_in: int,
    actual_out: int,
    tolerance: float = DEFAULT_TOLERANCE,
    max_frames: int | None = None,
    label: str | None = None,
    mode: str = "real",
    model: str | None = None,
) -> VideoEvaluation:
    """Прогоняет видео через счётчик и возвращает метрики точности."""
    try:
        import cv2
    except ImportError as exc:
        raise EvaluationError(
            "OpenCV не установлен. Установите зависимости: pip install -r requirements.txt",
            code=EXIT_DEPENDENCY,
        ) from exc

    path = Path(video_path)
    if not path.exists():
        raise EvaluationError(f"Файл видео не найден: {path}")
    if not path.is_file():
        raise EvaluationError(f"Ожидался файл, а не папка: {path}")

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise EvaluationError(f"Не удалось открыть видео (кодек/контейнер не поддержан): {path}")

    reported_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = 0
    last_stats: dict[str, Any] | None = None
    started = time.perf_counter()

    try:
        while True:
            if max_frames is not None and frames >= max_frames:
                break
            ok, frame = capture.read()
            if not ok:
                break
            _, stats = counter.process_frame(frame)
            last_stats = stats
            frames += 1
    finally:
        capture.release()

    elapsed = time.perf_counter() - started
    if frames == 0 or last_stats is None:
        raise EvaluationError(f"Видео не содержит читаемых кадров: {path}")

    if "entered" not in last_stats or "exited" not in last_stats:
        raise EvaluationError("Счётчик вернул stats без ключей entered/exited - нарушен контракт PROJECT_SPEC.md 3.1")

    auto_in = int(last_stats["entered"])
    auto_out = int(last_stats["exited"])

    return VideoEvaluation(
        video=str(path),
        mode=mode,
        frames=frames,
        elapsed_s=elapsed,
        fps=frames / elapsed if elapsed > 0 else 0.0,
        video_fps=reported_fps or None,
        entered=compute_metrics(actual_in, auto_in),
        exited=compute_metrics(actual_out, auto_out),
        tolerance=tolerance,
        label=label,
        model=model,
    )


# ---------------------------------------------------------------------------
# Вывод
# ---------------------------------------------------------------------------


def format_report(result: VideoEvaluation) -> str:
    """Человекочитаемый отчёт по одному видео."""
    lines = [
        f"Видео: {result.video}",
        f"Режим: {'mock (MockVisitorCounter, без YOLO)' if result.mode == 'mock' else 'real (VisitorCounter)'}",
        (
            f"Кадров: {result.frames} | Время: {result.elapsed_s:.3f} с | "
            f"FPS обработки: {result.fps:.1f}"
            + (f" | FPS видео: {result.video_fps:.1f}" if result.video_fps else "")
        ),
        "",
        f"{'Показатель':<12} {'Факт':>6} {'Авто':>6} {'|Авто-Факт|':>12} {'Ошибка, %':>14}",
        result.entered.as_row("Вошло"),
        result.exited.as_row("Вышло"),
        "",
        f"Порог: {result.tolerance:.2f}% | Итог: {'PASS' if result.passed else 'FAIL'}",
    ]
    return "\n".join(lines)


def write_json(path: str, payload: dict[str, Any]) -> None:
    """Пишет JSON в файл (или в stdout при path == "-")."""
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if path == "-":
        print(text)
        return
    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evaluate_accuracy.py",
        description="Оценка точности подсчёта посетителей на одном видео.",
        epilog=(
            "Пример: python tests/evaluate_accuracy.py storage/test_videos/simple.mp4 "
            "--actual-in 10 --actual-out 9 --mock"
        ),
    )
    parser.add_argument("video", metavar="VIDEO", help="путь к видеофайлу (.mp4/.avi)")
    parser.add_argument("--actual-in", type=int, required=True, help="фактическое число вошедших")
    parser.add_argument("--actual-out", type=int, required=True, help="фактическое число вышедших")
    parser.add_argument("--mock", action="store_true", help="использовать MockVisitorCounter вместо YOLO")
    parser.add_argument("--model", default=None, help="путь к весам (по умолчанию yolov8n.pt)")
    parser.add_argument("--conf", type=float, default=0.35, help="порог уверенности детектора (0..1)")
    parser.add_argument(
        "--line",
        default=None,
        help='виртуальная линия в формате "x1,y1,x2,y2" (по умолчанию - центр кадра)',
    )
    parser.add_argument("--max-frames", type=int, default=None, help="обработать только первые N кадров")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"допустимая ошибка в процентах (по умолчанию {DEFAULT_TOLERANCE})",
    )
    parser.add_argument(
        "--fail-over",
        action="store_true",
        help="вернуть код 3, если ошибка превысила --tolerance (удобно для CI)",
    )
    parser.add_argument("--json", dest="json_path", default=None, help='файл для JSON-результата ("-" - stdout)')
    parser.add_argument("--label", default=None, help="метка видео для отчёта (например, simple/medium/hard)")
    parser.add_argument("--quiet", action="store_true", help="не печатать человекочитаемый отчёт")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.actual_in < 0 or args.actual_out < 0:
        parser.error("--actual-in и --actual-out не могут быть отрицательными")
    if args.tolerance <= 0:
        parser.error("--tolerance должен быть больше нуля")
    if args.max_frames is not None and args.max_frames <= 0:
        parser.error("--max-frames должен быть больше нуля")
    if not 0.0 < args.conf <= 1.0:
        parser.error("--conf должен быть в диапазоне (0, 1]")

    try:
        line = parse_line(args.line) if args.line else None
    except ValueError as exc:
        parser.error(str(exc))
        return EXIT_USAGE  # недостижимо, но сохраняет типизацию mypy

    try:
        counter, mode = build_counter(
            mock=args.mock,
            model=args.model,
            conf=args.conf,
            line=line,
        )
        result = evaluate_video(
            args.video,
            counter,
            actual_in=args.actual_in,
            actual_out=args.actual_out,
            tolerance=args.tolerance,
            max_frames=args.max_frames,
            label=args.label,
            mode=mode,
            model=args.model,
        )
    except EvaluationError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return exc.code

    json_stdout = args.json_path == "-"
    if not args.quiet and not json_stdout:
        print(format_report(result))
        print()

    payload = result.to_dict()
    if args.json_path:
        write_json(args.json_path, payload)
        if not args.quiet and not json_stdout:
            print(f"JSON сохранён: {args.json_path}")

    if not result.passed and args.fail_over:
        return EXIT_THRESHOLD

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
