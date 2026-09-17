#!/usr/bin/env python3
"""Export prediction JSONL to the official Spider evaluator text formats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def one_line(value: Any) -> str:
    return " ".join(str(value).replace("\t", " ").splitlines()).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--gold-output", required=True, type=Path)
    parser.add_argument("--pred-output", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.input)
    args.gold_output.parent.mkdir(parents=True, exist_ok=True)
    args.pred_output.parent.mkdir(parents=True, exist_ok=True)
    with args.gold_output.open("w", encoding="utf-8") as gold_handle, args.pred_output.open(
        "w", encoding="utf-8"
    ) as pred_handle:
        for row in rows:
            gold_handle.write(f"{one_line(row['target_sql'])}\t{row['db_id']}\n")
            pred_handle.write(one_line(row["prediction"]) + "\n")
    print(f"Exported {len(rows)} examples for the official Spider evaluator")


if __name__ == "__main__":
    main()
