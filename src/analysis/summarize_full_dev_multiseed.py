#!/usr/bin/env python3
"""Aggregate full Spider development-set results across training seeds."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


METHODS = ("random", "uncertainty", "uncertainty_schema_diverse")


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def official_exact(path: Path) -> float:
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"^exact match\s+(.+)$", text, flags=re.MULTILINE)
    if not matches:
        raise ValueError(f"Could not find exact-match row in {path}")
    return float(matches[-1].split()[-1])


def aggregate(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "sample_std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    args = parser.parse_args()

    result: dict = {
        "seeds": args.seeds,
        "development_examples": 1034,
        "methods": {},
        "metric": "official Spider exact match",
        "standard_deviation": "sample standard deviation across training seeds",
        "metric_boundary": (
            "Official Spider exact match on all 1,034 development examples. "
            "Execution accuracy is not reported because the legacy Spider database "
            "package triggered a text-decoding failure under modern Python."
        ),
        "method_boundary": (
            "The uncertainty-based selectors are lightweight static methods inspired "
            "by LEAD concepts, not a reproduction of LEAD's online IDU and bandit method."
        ),
    }

    for method in METHODS:
        runs = []
        for seed in args.seeds:
            run_dir = args.experiment_dir / f"seed_{seed}" / method
            diagnostic = read_json(run_dir / "full_dev_eval" / "eval_metrics.json")
            runs.append(
                {
                    "seed": seed,
                    "official_spider_exact_match": official_exact(
                        run_dir / "full_dev_official" / "evaluation.txt"
                    ),
                    "diagnostic_normalized_exact_match": diagnostic[
                        "normalized_exact_match"
                    ],
                    "generation_seconds": diagnostic["generation_seconds"],
                }
            )

        exact_scores = [run["official_spider_exact_match"] for run in runs]
        result["methods"][method] = {
            "runs": runs,
            "official_spider_exact_match": aggregate(exact_scores),
        }

    random_mean = result["methods"]["random"]["official_spider_exact_match"]["mean"]
    for method in METHODS:
        method_mean = result["methods"][method]["official_spider_exact_match"]["mean"]
        result["methods"][method]["absolute_gain_over_random"] = (
            method_mean - random_mean
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
