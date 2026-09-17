#!/usr/bin/env python3
"""Select equal-budget Spider subsets from a pre-scored candidate pool."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def random_select(rows: list[dict[str, Any]], budget: int, seed: int) -> list[dict[str, Any]]:
    return random.Random(seed).sample(rows, budget)


def uncertainty_select(rows: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: row["pretrained_target_loss"], reverse=True)[:budget]


def diverse_uncertainty_select(rows: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    """Round-robin databases within complexity strata, prioritising high loss."""
    complexity_counts = Counter(row["complexity"] for row in rows)
    total = len(rows)
    quotas = {
        key: round(budget * count / total) for key, count in complexity_counts.items()
    }
    while sum(quotas.values()) < budget:
        key = max(complexity_counts, key=lambda item: complexity_counts[item] - quotas[item])
        quotas[key] += 1
    while sum(quotas.values()) > budget:
        key = max(quotas, key=quotas.get)
        quotas[key] -= 1

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for complexity, quota in quotas.items():
        grouped: dict[str, deque[dict[str, Any]]] = {}
        candidates = [row for row in rows if row["complexity"] == complexity]
        by_database: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in candidates:
            by_database[row["db_id"]].append(row)
        for db_id, db_rows in by_database.items():
            grouped[db_id] = deque(
                sorted(db_rows, key=lambda row: row["pretrained_target_loss"], reverse=True)
            )
        database_order = sorted(
            grouped, key=lambda db_id: grouped[db_id][0]["pretrained_target_loss"], reverse=True
        )
        while quota > 0 and database_order:
            next_order: list[str] = []
            for db_id in database_order:
                if quota == 0:
                    break
                row = grouped[db_id].popleft()
                selected.append(row)
                selected_ids.add(row["id"])
                quota -= 1
                if grouped[db_id]:
                    next_order.append(db_id)
            database_order = next_order

    if len(selected) < budget:
        remainder = [
            row for row in uncertainty_select(rows, len(rows)) if row["id"] not in selected_ids
        ]
        selected.extend(remainder[: budget - len(selected)])
    return selected


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--budget", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.input)
    if not 0 < args.budget <= len(rows):
        raise ValueError("Budget must be between 1 and the candidate-pool size")
    methods = {
        "random": random_select(rows, args.budget, args.seed),
        "uncertainty": uncertainty_select(rows, args.budget),
        "uncertainty_schema_diverse": diverse_uncertainty_select(rows, args.budget),
    }
    summary: dict[str, Any] = {}
    for name, selected in methods.items():
        write_jsonl(selected, args.output_dir / f"{name}.jsonl")
        summary[name] = {
            "samples": len(selected),
            "databases": len({row["db_id"] for row in selected}),
            "complexity": dict(Counter(row["complexity"] for row in selected)),
            "mean_pretrained_target_loss": sum(
                row["pretrained_target_loss"] for row in selected
            )
            / len(selected),
        }
    (args.output_dir / "selection_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
