#!/usr/bin/env python
"""Генерирует короткое синтетическое видео для самопроверки CLI-утилит.

Зачем: `tests/evaluate_accuracy.py --mock` нужно на чём-то проверить ещё до
появления реальных записей. Этот ролик - просто цветные кадры без людей:
он проверяет работоспособность скрипта, а НЕ точность модели. Использовать его
в отчёте как результат замера точности нельзя.

Пример:
    python tests/make_test_video.py
    python tests/make_test_video.py --out .tmp/clip.avi --frames 12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Создать синтетическое видео для smoke-проверки CLI.")
    parser.add_argument("--out", default="storage/test_videos/synthetic_40f.avi", help="куда сохранить файл")
    parser.add_argument("--frames", type=int, default=40, help="число кадров (по умолчанию 40)")
    parser.add_argument("--width", type=int, default=320, help="ширина кадра")
    parser.add_argument("--height", type=int, default=240, help="высота кадра")
    parser.add_argument("--fps", type=float, default=10.0, help="частота кадров")
    args = parser.parse_args(argv)

    try:
        import cv2
    except ImportError:
        print("OpenCV не установлен: pip install -r requirements.txt", file=sys.stderr)
        return 4

    import numpy as np

    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)

    writer = cv2.VideoWriter(
        str(target),
        cv2.VideoWriter_fourcc(*"MJPG"),
        args.fps,
        (args.width, args.height),
    )
    if not writer.isOpened():
        print(f"Не удалось открыть VideoWriter для {target} (кодек MJPG)", file=sys.stderr)
        return 2

    try:
        for index in range(args.frames):
            frame = np.zeros((args.height, args.width, 3), dtype=np.uint8)
            frame[:, :, 0] = (index * 6) % 256
            writer.write(frame)
    finally:
        writer.release()

    if not target.exists() or target.stat().st_size == 0:
        print(f"Файл не записался: {target}", file=sys.stderr)
        return 2

    print(f"Создано синтетическое видео: {target} ({args.frames} кадров, {args.width}x{args.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
