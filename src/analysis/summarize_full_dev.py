#!/usr/bin/env python3
"""Summarise full Spider development-set evaluation for each selection method."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


METHODS = ("random", "uncertainty", "uncertainty_schema_diverse")
DIFFICULTIES = ("easy", "medium", "hard", "extra", "all")


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def official_exact(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"^exact match\s+(.+)$", text, flags=re.MULTILINE)
    if not matches:
        raise ValueError(f"Could not find exact-match row in {path}")
    values = [float(value) for value in matches[-1].split()]
    if len(values) != len(DIFFICULTIES):
        raise ValueError(f"Unexpected exact-match row in {path}: {matches[-1]}")
    return dict(zip(DIFFICULTIES, values, strict=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = {"seed": int(args.seed_dir.name.removeprefix("seed_")), "methods": {}}
    for method in METHODS:
        run_dir = args.seed_dir / method
        evaluation = read_json(run_dir / "full_dev_eval" / "eval_metrics.json")
        result["methods"][method] = {
            "eval_samples": evaluation["eval_samples"],
            "eval_databases": evaluation["database_count"],
            "generation_seconds": evaluation["generation_seconds"],
            "diagnostic_normalized_exact_match": evaluation[
                "normalized_exact_match"
            ],
            "official_spider_exact_match": official_exact(
                run_dir / "full_dev_official" / "evaluation.txt"
            ),
        }

    result["metric_boundary"] = (
        "Official Spider exact match on all 1,034 development examples. "
        "Execution accuracy is not reported because the legacy Spider database "
        "package triggered a text-decoding failure under modern Python."
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
