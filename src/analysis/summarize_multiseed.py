#!/usr/bin/env python3
"""Summarise a completed multi-seed Spider data-selection experiment."""

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
        raise ValueError(f"Could not find overall exact match in {path}")
    return float(matches[-1].split()[-1])


def aggregate(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "sample_std": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 42, 73])
    args = parser.parse_args()

    result: dict = {
        "seeds": args.seeds,
        "methods": {},
        "standard_deviation": "sample standard deviation across training seeds",
        "metric_boundary": (
            "Official Spider exact match on the same fixed 100-example development subset. "
            "Execution accuracy is not reported because the legacy Spider database package "
            "triggered a text-decoding failure under modern Python."
        ),
        "method_boundary": (
            "Static pretrained-loss uncertainty methods inspired by LEAD concepts; not an "
            "official reproduction of LEAD IDU or its online bandit algorithm."
        ),
    }

    for method in METHODS:
        runs = []
        for seed in args.seeds:
            seed_dir = args.experiment_dir / f"seed_{seed}"
            selection = read_json(seed_dir / "subsets" / "selection_summary.json")[method]
            train = read_json(seed_dir / method / "model" / "train_metrics.json")
            diagnostic = read_json(seed_dir / method / "eval" / "eval_metrics.json")
            exact = official_exact(seed_dir / method / "official" / "evaluation.txt")
            runs.append(
                {
                    "seed": seed,
                    "selected_databases": selection["databases"],
                    "selected_mean_pretrained_target_loss": selection[
                        "mean_pretrained_target_loss"
                    ],
                    "train_seconds": train["train_seconds"],
                    "mean_train_loss": train["mean_loss"],
                    "diagnostic_normalized_exact_match": diagnostic[
                        "normalized_exact_match"
                    ],
                    "official_spider_exact_match": exact,
                }
            )

        result["methods"][method] = {
            "runs": runs,
            "aggregate": {
                key: aggregate([float(run[key]) for run in runs])
                for key in (
                    "selected_databases",
                    "train_seconds",
                    "official_spider_exact_match",
                )
            },
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
