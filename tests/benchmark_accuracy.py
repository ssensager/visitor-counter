#!/usr/bin/env python
"""Пакетный замер точности по списку видео и markdown-таблица для отчёта.

Скрипт - обёртка над `tests/evaluate_accuracy.py`: прогоняет несколько видео
(обычно три: простое, среднее, сложное) и собирает готовую таблицу для
`reports/05_devops_qa.md` и `reports/00_FINAL_SUMMARY.md`.

Примеры:

    # Заготовка пустой таблицы для отчёта (без запуска видео)
    python tests/benchmark_accuracy.py --table-template

    # Реальный прогон по манифесту
    python tests/benchmark_accuracy.py --manifest tests/accuracy_manifest.example.json \\
        --out reports/accuracy_table.md

    # Проверка самого скрипта без YOLO
    python tests/benchmark_accuracy.py --manifest tests/accuracy_manifest.example.json --mock

Формат манифеста (JSON):
    {
      "videos": [
        {
          "name": "Простое",
          "complexity": "простое",
          "path": "storage/test_videos/01_simple.mp4",
          "actual_in": 10,
          "actual_out": 9
        }
      ]
    }

Важно: числа `actual_in` / `actual_out` заполняются вручную после просмотра
видео. Скрипт не придумывает фактические значения и не подгоняет результаты.

Коды возврата: 0 - все видео посчитаны, 1 - были ошибки/незаполненные данные,
2 - ошибка аргументов.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

try:  # запуск как скрипт (python tests/benchmark_accuracy.py)
    from evaluate_accuracy import (
        DEFAULT_TOLERANCE,
        EvaluationError,
        VideoEvaluation,
        build_counter,
        evaluate_video,
        write_json,
    )
except ImportError:  # импорт из другого места
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from evaluate_accuracy import (  # type: ignore[no-redef]
        DEFAULT_TOLERANCE,
        EvaluationError,
        VideoEvaluation,
        build_counter,
        evaluate_video,
        write_json,
    )

EXIT_OK = 0
EXIT_FAILURES = 1
EXIT_USAGE = 2

DASH = "—"
TABLE_HEADER = (
    "| № | Сложность | Видео | Факт (вошло/вышло) | Авто (вошло/вышло) | "
    "Ошибка вход, % | Ошибка выход, % | FPS | Ориентир <= 5% |"
)
TABLE_ALIGN = "| :-: | :--- | :--- | :---: | :---: | ---: | ---: | ---: | :-: |"


# ---------------------------------------------------------------------------
# Манифест
# ---------------------------------------------------------------------------


def load_manifest(path: str | Path) -> list[dict[str, Any]]:
    """Читает манифест: поддерживает {"videos": [...]} и просто список."""
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise EvaluationError(f"Манифест не найден: {manifest_path}")

    try:
        # utf-8-sig: блокнот Windows сохраняет JSON с BOM, а json.loads его не переносит.
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise EvaluationError(f"Манифест не является корректным JSON: {exc}") from exc

    if isinstance(payload, dict):
        videos = payload.get("videos")
    elif isinstance(payload, list):
        videos = payload
    else:
        videos = None

    if not isinstance(videos, list) or not videos:
        raise EvaluationError('Манифест должен содержать непустой список "videos"')

    return videos


def _require_int(entry: dict[str, Any], key: str) -> int:
    value = entry.get(key)
    if value is None:
        raise EvaluationError(
            f'В манифесте не заполнено поле "{key}" для видео {entry.get("path", "?")}: '
            "укажите фактическое число после просмотра видео"
        )
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvaluationError(f'Поле "{key}" должно быть целым числом, получено: {value!r}')
    if value < 0:
        raise EvaluationError(f'Поле "{key}" не может быть отрицательным: {value}')
    return value


# ---------------------------------------------------------------------------
# Таблица
# ---------------------------------------------------------------------------


def _fmt_pct(metrics: Any) -> str:
    if metrics is None:
        return DASH
    if metrics.error_pct is None:
        return f"{metrics.abs_error} (абс.)"
    return f"{metrics.error_pct:.2f}"


def build_markdown_table(
    results: Sequence[VideoEvaluation | None],
    *,
    errors: Sequence[str | None] | None = None,
    template_only: bool = False,
) -> str:
    """Собирает markdown-таблицу. template_only=True - пустая заготовка на 3 видео."""
    lines = ["", TABLE_HEADER, TABLE_ALIGN]

    if template_only:
        for index, complexity in enumerate(("простое", "среднее", "сложное"), start=1):
            lines.append(
                f"| {index} | {complexity} | `<путь к видео>` | {DASH} | {DASH} | {DASH} | {DASH} | {DASH} | {DASH} |"
            )
        return "\n".join(lines)

    for index, result in enumerate(results, start=1):
        error = errors[index - 1] if errors else None
        if result is None:
            lines.append(
                f"| {index} | {DASH} | {DASH} | {DASH} | {DASH} | {DASH} | {DASH} | {DASH} | FAIL: {error or 'нет данных'} |"
            )
            continue

        fact = f"{result.entered.actual} / {result.exited.actual}"
        auto = f"{result.entered.auto} / {result.exited.auto}"
        verdict = "PASS" if result.passed else "FAIL"
        lines.append(
            f"| {index} | {result.label or DASH} | `{Path(result.video).name}` | {fact} | {auto} | "
            f"{_fmt_pct(result.entered)} | {_fmt_pct(result.exited)} | {result.fps:.1f} | {verdict} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchmark_accuracy.py",
        description="Пакетный замер точности подсчёта по манифесту видео и markdown-таблица.",
        epilog=(
            "Пример: python tests/benchmark_accuracy.py "
            "--manifest tests/accuracy_manifest.example.json --out reports/accuracy_table.md"
        ),
    )
    parser.add_argument("--manifest", default=None, help="JSON-манифест со списком видео")
    parser.add_argument("--mock", action="store_true", help="использовать MockVisitorCounter")
    parser.add_argument("--model", default=None, help="путь к весам (по умолчанию yolov8n.pt)")
    parser.add_argument("--conf", type=float, default=0.35, help="порог уверенности детектора")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"допустимая ошибка в процентах (по умолчанию {DEFAULT_TOLERANCE})",
    )
    parser.add_argument("--max-frames", type=int, default=None, help="ограничить число кадров на видео")
    parser.add_argument("--out", default=None, help="куда сохранить markdown-таблицу")
    parser.add_argument("--json-out", dest="json_out", default=None, help="куда сохранить JSON с деталями")
    parser.add_argument(
        "--table-template",
        action="store_true",
        help="напечатать пустую заготовку таблицы на 3 видео и выйти",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.table_template:
        print(build_markdown_table([], template_only=True).lstrip("\n"))
        return EXIT_OK

    if not args.manifest:
        parser.error("укажите --manifest или --table-template")

    try:
        videos = load_manifest(args.manifest)
    except EvaluationError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return EXIT_USAGE

    results: list[VideoEvaluation | None] = []
    errors: list[str | None] = []
    payload: list[dict[str, Any]] = []

    for entry in videos:
        path = entry.get("path")
        label = entry.get("complexity") or entry.get("name")
        name = entry.get("name") or path

        try:
            if not path:
                raise EvaluationError(f'В манифесте не указан "path" для записи {name!r}')
            actual_in = _require_int(entry, "actual_in")
            actual_out = _require_int(entry, "actual_out")

            counter, mode = build_counter(mock=args.mock, model=args.model, conf=args.conf)
            result = evaluate_video(
                path,
                counter,
                actual_in=actual_in,
                actual_out=actual_out,
                tolerance=args.tolerance,
                max_frames=args.max_frames,
                label=str(label) if label else None,
                mode=mode,
                model=args.model,
            )
        except EvaluationError as exc:
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
            results.append(None)
            errors.append(str(exc))
            payload.append({"name": name, "path": path, "error": str(exc)})
            continue

        print(f"[OK] {name}: ошибка вход={_fmt_pct(result.entered)}%, выход={_fmt_pct(result.exited)}%")
        results.append(result)
        errors.append(None)
        payload.append(result.to_dict())

    table = build_markdown_table(results, errors=errors)
    print(table)

    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("## Точность подсчёта\n" + table + "\n", encoding="utf-8")
        print(f"\nТаблица сохранена: {target}")

    if args.json_out:
        write_json(args.json_out, {"tolerance_pct": args.tolerance, "videos": payload})
        print(f"JSON сохранён: {args.json_out}")

    failed = sum(1 for result in results if result is None or not result.passed)
    total = len(results)
    print(f"\nИтого: {total - failed} из {total} в пределах {args.tolerance:.2f}%")

    return EXIT_FAILURES if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
