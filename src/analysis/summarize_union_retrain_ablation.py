#!/usr/bin/env python3
"""Summarise the fresh-union retraining ablation against existing controls."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required-metrics", required=True, type=Path)
    parser.add_argument("--ablation-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    required = read_json(args.required_metrics)
    random_by_seed = {
        int(row["seed"]): float(row["official_spider_exact_match"])
        for row in required["methods"]["random"]["runs"]
    }
    continuation_by_seed = {
        int(row["seed"]): float(row["official_spider_exact_match"])
        for row in required["methods"]["iterative_lead"]["runs"]
    }

    runs = []
    for seed in args.seeds:
        run_dir = args.ablation_dir / f"seed_{seed}"
        summary = read_json(run_dir / "experiment_summary.json")
        score = official_exact(run_dir / "official" / "evaluation.txt")
        runs.append({
            "seed": seed,
            "official_spider_exact_match": score,
            "random_exact_match": random_by_seed[seed],
            "sequential_continuation_exact_match": continuation_by_seed[seed],
            "difference_vs_random": score - random_by_seed[seed],
            "difference_vs_sequential_continuation": score - continuation_by_seed[seed],
            "selected_databases": summary["selected_databases"],
            "retrain_and_evaluate_seconds": summary["retrain_and_evaluate_seconds"],
        })

    scores = [row["official_spider_exact_match"] for row in runs]
    vs_random = [row["difference_vs_random"] for row in runs]
    vs_continuation = [row["difference_vs_sequential_continuation"] for row in runs]
    result = {
        "question": (
            "Does fresh retraining on the union of both iterative batches recover "
            "performance lost by sequential new-batch-only training?"
        ),
        "controlled_setup": {
            "model": "Salesforce/codet5-small",
            "selected_budget": 500,
            "fresh_training_epochs": 3,
            "development_examples": 1034,
            "seeds": args.seeds,
        },
        "runs": runs,
        "aggregate": {
            "official_spider_exact_match": aggregate(scores),
            "difference_vs_random": aggregate(vs_random),
            "difference_vs_sequential_continuation": aggregate(vs_continuation),
            "wins_vs_random": sum(value > 0 for value in vs_random),
            "wins_vs_sequential_continuation": sum(value > 0 for value in vs_continuation),
            "retrain_and_evaluate_seconds": aggregate(
                [row["retrain_and_evaluate_seconds"] for row in runs]
            ),
        },
        "interpretation_boundary": (
            "This diagnostic isolates final training protocol from selected-subset "
            "quality. It does not erase the computational cost used to obtain the "
            "iterative selection."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
