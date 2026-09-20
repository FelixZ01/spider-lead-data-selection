#!/usr/bin/env python3
"""Summarise the required full-data, random, and iterative comparisons."""

from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path


METHODS = ("full_data", "random", "iterative_lead")


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
    parser.add_argument("--baseline-dir", required=True, type=Path)
    parser.add_argument("--iterative-dir", required=True, type=Path)
    parser.add_argument("--scoring-metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    offline_scoring = float(read_json(args.scoring_metrics)["scoring_seconds"])
    methods: dict[str, dict] = {}

    for method in ("full_data", "random"):
        runs = []
        for seed in args.seeds:
            run_dir = args.baseline_dir / f"seed_{seed}" / method
            summary = read_json(run_dir / "experiment_summary.json")
            timings = summary["timings"]
            runs.append({
                "seed": seed,
                "official_spider_exact_match": official_exact(
                    run_dir / "official" / "evaluation.txt"
                ),
                "selected_samples": summary["selected_samples"],
                "selected_databases": summary["selected_databases"],
                "selection_or_scoring_seconds": timings["selection_seconds"],
                "training_seconds": timings["training_wall_seconds"],
                "evaluation_seconds": (
                    timings["evaluation_wall_seconds"]
                    + timings["official_evaluation_seconds"]
                ),
                "end_to_end_seconds": summary["end_to_end_seconds"],
            })
        methods[method] = {"runs": runs}

    iterative_runs = []
    for seed in args.seeds:
        run_dir = args.iterative_dir / f"seed_{seed}"
        summary = read_json(run_dir / "experiment_summary.json")
        timings = summary["stage_timings"]
        iterative_runs.append({
            "seed": seed,
            "official_spider_exact_match": official_exact(
                run_dir / "final_official" / "evaluation.txt"
            ),
            "selected_samples": summary["total_budget"],
            "selected_databases": summary["selected_databases_total"],
            "selection_or_scoring_seconds": (
                offline_scoring
                + timings["online_selection_seconds"]
                + timings["reward_update_seconds"]
            ),
            "training_seconds": timings["training_wall_seconds"],
            "evaluation_seconds": (
                timings["evaluation_wall_seconds"]
                + timings["official_evaluation_seconds"]
            ),
            "end_to_end_seconds": offline_scoring + summary["total_seconds"],
            "selected_arms": [
                item["selected_difficulty_cluster"]
                for item in summary["round_summaries"]
            ],
            "raw_rewards": [
                item["raw_idu_reduction_reward"]
                for item in summary["round_summaries"]
            ],
        })
    methods["iterative_lead"] = {"runs": iterative_runs}

    for method, values in methods.items():
        runs = values["runs"]
        values["aggregate"] = {
            key: aggregate([float(run[key]) for run in runs])
            for key in (
                "official_spider_exact_match",
                "selection_or_scoring_seconds",
                "training_seconds",
                "evaluation_seconds",
                "end_to_end_seconds",
            )
        }

    full_accuracy = methods["full_data"]["aggregate"][
        "official_spider_exact_match"
    ]["mean"]
    full_time = methods["full_data"]["aggregate"]["end_to_end_seconds"]["mean"]
    for method, values in methods.items():
        accuracy = values["aggregate"]["official_spider_exact_match"]["mean"]
        elapsed = values["aggregate"]["end_to_end_seconds"]["mean"]
        values["accuracy_difference_vs_full"] = accuracy - full_accuracy
        values["time_reduction_vs_full"] = 1.0 - elapsed / full_time

    result = {
        "research_questions": {
            "Q1": "Can selected data match or exceed full-data performance?",
            "Q2": "Does iterative selection outperform random selection at budget 500?",
            "Q3": "Does iterative selection improve the end-to-end performance-cost trade-off?",
        },
        "shared_setup": {
            "model": "Salesforce/codet5-small",
            "candidate_pool": 1000,
            "selected_budget": 500,
            "epochs": 3,
            "development_examples": 1034,
            "seeds": args.seeds,
        },
        "methods": methods,
        "metric": "official Spider exact match",
        "timing_boundary": (
            "End-to-end time is the sum of selection or scoring, model training, "
            "generation evaluation, and official exact-match evaluation. The fixed "
            "pretrained pool-scoring cost is included for iterative selection."
        ),
        "method_boundary": (
            "The iterative method is a two-round observed-loss-change adaptation "
            "with non-negative predicted-loss clipping, loss-quantile difficulty "
            "clusters, database-level task groups, and EXP3 scheduling. It is not "
            "the paper's inference-free gradient implementation."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
