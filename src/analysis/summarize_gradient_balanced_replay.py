#!/usr/bin/env python3
"""Summarise the balanced-cluster replay control against dynamic EXP3."""

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
    rows = re.findall(r"^exact match\s+(.+)$", text, flags=re.MULTILINE)
    if not rows:
        raise ValueError(f"Could not find exact-match row in {path}")
    return float(rows[-1].split()[-1])


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
    parser.add_argument("--dynamic-metrics", required=True, type=Path)
    parser.add_argument("--required-metrics", required=True, type=Path)
    parser.add_argument("--scoring-metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", required=True, type=int)
    args = parser.parse_args()

    dynamic = {
        int(row["seed"]): row
        for row in read_json(args.dynamic_metrics)["runs"]
    }
    required = read_json(args.required_metrics)
    random_runs = {
        int(row["seed"]): row
        for row in required["methods"]["random"]["runs"]
    }
    offline_scoring = float(read_json(args.scoring_metrics)["scoring_seconds"])

    runs = []
    for seed in args.seeds:
        run_dir = args.experiment_dir / f"seed_{seed}"
        summary = read_json(run_dir / "experiment_summary.json")
        timings = summary["stage_timings"]
        score = official_exact(run_dir / "final_official" / "evaluation.txt")
        dynamic_score = float(dynamic[seed]["official_spider_exact_match"])
        random_score = float(random_runs[seed]["official_spider_exact_match"])
        runs.append(
            {
                "seed": seed,
                "official_spider_exact_match": score,
                "dynamic_exp3_exact_match": dynamic_score,
                "random_exact_match": random_score,
                "difference_vs_dynamic_exp3": score - dynamic_score,
                "difference_vs_random": score - random_score,
                "selected_databases": int(summary["selected_databases_total"]),
                "selected_arms": [
                    row["selected_difficulty_cluster"]
                    for row in summary["round_summaries"]
                ],
                "selection_or_scoring_seconds": (
                    offline_scoring
                    + float(timings["online_selection_seconds"])
                    + float(timings["reward_update_seconds"])
                ),
                "training_seconds": float(timings["training_wall_seconds"]),
                "evaluation_seconds": (
                    float(timings["evaluation_wall_seconds"])
                    + float(timings["official_evaluation_seconds"])
                ),
                "end_to_end_seconds": offline_scoring + float(summary["total_seconds"]),
            }
        )

    numeric_keys = (
        "official_spider_exact_match",
        "difference_vs_dynamic_exp3",
        "difference_vs_random",
        "selected_databases",
        "selection_or_scoring_seconds",
        "training_seconds",
        "evaluation_seconds",
        "end_to_end_seconds",
    )
    result = {
        "question": (
            "Does adaptive EXP3 allocation outperform a fixed balanced difficulty "
            "schedule when gradient utility, database grouping, cumulative replay, "
            "data budget, and optimizer-step budget are held constant?"
        ),
        "controlled_setup": {
            "model": "Salesforce/codet5-small",
            "candidate_pool": 1000,
            "selected_budget": 500,
            "selection_rounds": 5,
            "balanced_arm_schedule": [0, 1, 0, 1, 0],
            "training_mode": "cumulative_union",
            "round_optimizer_steps": [100, 200, 300, 400, 500],
            "total_optimizer_steps": 1500,
            "development_examples": 1034,
            "seeds": args.seeds,
        },
        "runs": runs,
        "aggregate": {
            key: aggregate([float(row[key]) for row in runs])
            for key in numeric_keys
        },
        "wins_vs_dynamic_exp3": sum(
            row["difference_vs_dynamic_exp3"] > 0 for row in runs
        ),
        "wins_vs_random": sum(row["difference_vs_random"] > 0 for row in runs),
        "offline_pretrained_scoring_seconds": offline_scoring,
        "metric": "official Spider exact match",
        "timing_boundary": (
            "End-to-end time includes shared pretrained pool scoring, selection, "
            "cumulative training, generation, and official evaluation."
        ),
        "method_boundary": (
            "This control removes EXP3 and fixes the difficulty-cluster sequence, "
            "while preserving every other component and budget of the dynamic "
            "gradient replay adaptation."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
