#!/usr/bin/env python
"""Prepare PaddleClas file lists for the 12-class cat dataset."""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Project root directory.")
    parser.add_argument("--source-list", default="train_list.txt")
    parser.add_argument("--train-dir", default="cat_12_train")
    parser.add_argument("--test-dir", default="cat_12_test")
    parser.add_argument("--out-dir", default="paddleclas_data")
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=2026)
    return parser.parse_args()


def to_posix(path: Path) -> str:
    return path.as_posix()


def parse_label_line(line: str) -> tuple[str, int]:
    parts = line.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Bad label line: {line!r}")
    return parts[0].replace("\\", "/"), int(parts[1])


def resolve_train_path(root: Path, listed_path: str, train_dir: str) -> str:
    listed = Path(listed_path)
    candidates = [
        root / listed,
        root / train_dir / listed,
        root / train_dir / listed.name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return to_posix(candidate.relative_to(root))

    matches = sorted((root / train_dir).rglob(listed.name))
    if len(matches) == 1:
        return to_posix(matches[0].relative_to(root))
    if len(matches) > 1:
        raise FileNotFoundError(f"Ambiguous image name {listed.name}: {matches}")
    raise FileNotFoundError(f"Cannot find image for {listed_path}")


def collect_test_images(root: Path, test_dir: str) -> list[str]:
    base = root / test_dir
    if not base.exists():
        return []
    images = [
        path
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    ]
    return [to_posix(path.relative_to(root)) for path in sorted(images)]


def write_labeled_list(path: Path, rows: list[tuple[str, int]]) -> None:
    path.write_text(
        "".join(f"{image_path} {label}\n" for image_path, label in rows),
        encoding="utf-8",
    )


def write_plain_list(path: Path, rows: list[str]) -> None:
    path.write_text("".join(f"{image_path}\n" for image_path in rows), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if not 0.0 < args.val_ratio < 1.0:
        raise ValueError("--val-ratio must be between 0 and 1")

    root = Path(args.root).resolve()
    source_list = root / args.source_list
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    by_label: dict[int, list[str]] = defaultdict(list)
    for raw_line in source_list.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        listed_path, label = parse_label_line(raw_line)
        resolved_path = resolve_train_path(root, listed_path, args.train_dir)
        by_label[label].append(resolved_path)

    rng = random.Random(args.seed)
    train_rows: list[tuple[str, int]] = []
    val_rows: list[tuple[str, int]] = []
    full_rows: list[tuple[str, int]] = []

    for label in sorted(by_label):
        paths = sorted(by_label[label])
        rng.shuffle(paths)
        val_count = max(1, round(len(paths) * args.val_ratio))
        val_paths = paths[:val_count]
        train_paths = paths[val_count:]
        train_rows.extend((path, label) for path in train_paths)
        val_rows.extend((path, label) for path in val_paths)
        full_rows.extend((path, label) for path in paths)

    rng.shuffle(train_rows)
    rng.shuffle(val_rows)
    rng.shuffle(full_rows)

    write_labeled_list(out_dir / "train_list.txt", train_rows)
    write_labeled_list(out_dir / "val_list.txt", val_rows)
    write_labeled_list(out_dir / "train_full_list.txt", full_rows)
    write_plain_list(out_dir / "test_images.txt", collect_test_images(root, args.test_dir))

    label_lines = [f"{label} class_{label}\n" for label in sorted(by_label)]
    (out_dir / "label_list.txt").write_text("".join(label_lines), encoding="utf-8")

    print(f"Wrote {out_dir / 'train_list.txt'}: {len(train_rows)} images")
    print(f"Wrote {out_dir / 'val_list.txt'}: {len(val_rows)} images")
    print(f"Wrote {out_dir / 'train_full_list.txt'}: {len(full_rows)} images")
    print(f"Wrote {out_dir / 'test_images.txt'}")
    print(f"Labels: {sorted(by_label)}")


if __name__ == "__main__":
    main()
