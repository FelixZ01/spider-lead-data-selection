#!/usr/bin/env python3
"""Aggregate iterative LEAD-style Spider runs and compare existing baselines."""

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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", required=True, type=Path)
    parser.add_argument("--baseline-metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    args = parser.parse_args()

    runs = []
    for seed in args.seeds:
        seed_dir = args.experiment_dir / f"seed_{seed}"
        summary = read_json(seed_dir / "experiment_summary.json")
        diagnostic = read_json(seed_dir / "final_eval" / "eval_metrics.json")
        runs.append({
            "seed": seed,
            "official_spider_exact_match": official_exact(
                seed_dir / "final_official" / "evaluation.txt"
            ),
            "diagnostic_normalized_exact_match": diagnostic["normalized_exact_match"],
            "selected_databases": summary["selected_databases_total"],
            "total_seconds": summary["total_seconds"],
            "selected_arms": [
                item["selected_difficulty_cluster"]
                for item in summary["round_summaries"]
            ],
            "raw_rewards": [
                item["raw_idu_reduction_reward"]
                for item in summary["round_summaries"]
            ],
        })

    scores = [run["official_spider_exact_match"] for run in runs]
    baselines = read_json(args.baseline_metrics)["methods"]
    iterative_mean = statistics.mean(scores)
    comparisons = {
        method: iterative_mean - values["official_spider_exact_match"]["mean"]
        for method, values in baselines.items()
    }
    result = {
        "method": "simplified_iterative_lead",
        "seeds": args.seeds,
        "runs": runs,
        "official_spider_exact_match": aggregate(scores),
        "absolute_gain_vs_existing_baselines": comparisons,
        "metric": "official Spider exact match on all 1,034 development examples",
        "method_boundary": (
            "Two-round observed-loss-change adaptation with loss-quantile difficulty "
            "clusters and EXP3. It tests the LEAD workflow but does not reproduce the "
            "paper's inference-free gradient approximation or original task embeddings."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
