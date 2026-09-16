#!/usr/bin/env python3
"""Create reproducible Full and Random BIRD training baselines."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def sample_random(rows: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    if size < 1:
        raise ValueError("Random subset size must be at least 1")
    if size > len(rows):
        raise ValueError(f"Requested {size} rows, but input only has {len(rows)}")
    generator = random.Random(seed)
    chosen_indices = sorted(generator.sample(range(len(rows)), size))
    return [rows[index] for index in chosen_indices]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--random-size", type=int)
    group.add_argument("--random-fraction", type=float)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.input)
    if not rows:
        raise ValueError("Input dataset is empty")
    size = args.random_size
    if args.random_fraction is not None:
        if not 0 < args.random_fraction <= 1:
            raise ValueError("--random-fraction must be in (0, 1]")
        size = max(1, round(len(rows) * args.random_fraction))

    full_path = args.output_dir / "full.jsonl"
    random_path = args.output_dir / f"random_n{size}_seed{args.seed}.jsonl"
    write_jsonl(rows, full_path)
    write_jsonl(sample_random(rows, size, args.seed), random_path)
    print(f"Full baseline:   {len(rows)} rows -> {full_path}")
    print(f"Random baseline: {size} rows -> {random_path}")


if __name__ == "__main__":
    main()
