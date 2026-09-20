#!/usr/bin/env python3
"""Summarise multi-seed dynamic gradient LEAD runs with cumulative replay."""

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


def runs_by_seed(metrics: dict) -> dict[int, dict]:
    return {int(row["seed"]): row for row in metrics["runs"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", required=True, type=Path)
    parser.add_argument("--required-metrics", required=True, type=Path)
    parser.add_argument("--idu-metrics", required=True, type=Path)
    parser.add_argument("--previous-five-round-metrics", required=True, type=Path)
    parser.add_argument("--scoring-metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", required=True, type=int)
    args = parser.parse_args()

    required = read_json(args.required_metrics)
    idu = runs_by_seed(read_json(args.idu_metrics))
    previous = runs_by_seed(read_json(args.previous_five_round_metrics))
    offline_scoring = float(read_json(args.scoring_metrics)["scoring_seconds"])
    random_runs = {
        int(row["seed"]): row for row in required["methods"]["random"]["runs"]
    }
    full_runs = {
        int(row["seed"]): row
        for row in required["methods"]["full_data"]["runs"]
    }

    runs = []
    for seed in args.seeds:
        run_dir = args.experiment_dir / f"seed_{seed}"
        summary = read_json(run_dir / "experiment_summary.json")
        timings = summary["stage_timings"]
        score = official_exact(run_dir / "final_official" / "evaluation.txt")
        random_score = float(random_runs[seed]["official_spider_exact_match"])
        idu_score = float(idu[seed]["official_spider_exact_match"])
        previous_score = float(previous[seed]["official_spider_exact_match"])
        full_score = float(full_runs[seed]["official_spider_exact_match"])
        runs.append(
            {
                "seed": seed,
                "official_spider_exact_match": score,
                "random_exact_match": random_score,
                "observed_loss_idu_exact_match": idu_score,
                "previous_five_round_exact_match": previous_score,
                "full_data_exact_match": full_score,
                "difference_vs_random": score - random_score,
                "difference_vs_observed_loss_idu": score - idu_score,
                "difference_vs_previous_five_round": score - previous_score,
                "difference_vs_full_data": score - full_score,
                "selected_databases": int(summary["selected_databases_total"]),
                "selected_arms": [
                    item["selected_difficulty_cluster"]
                    for item in summary["round_summaries"]
                ],
                "bounded_rewards": [
                    item["bounded_exp3_reward"]
                    for item in summary["round_summaries"]
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
        "difference_vs_random",
        "difference_vs_observed_loss_idu",
        "difference_vs_previous_five_round",
        "difference_vs_full_data",
        "selected_databases",
        "selection_or_scoring_seconds",
        "training_seconds",
        "evaluation_seconds",
        "end_to_end_seconds",
    )
    result = {
        "question": (
            "Does cumulative replay make the dynamic gradient LEAD adaptation "
            "more accurate and stable than controlled baselines under the same "
            "500-example and 1,500-step budget?"
        ),
        "controlled_setup": {
            "model": "Salesforce/codet5-small",
            "candidate_pool": 1000,
            "selected_budget": 500,
            "selection_rounds": 5,
            "budget_per_round": 100,
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
        "wins_vs_random": sum(row["difference_vs_random"] > 0 for row in runs),
        "wins_vs_observed_loss_idu": sum(
            row["difference_vs_observed_loss_idu"] > 0 for row in runs
        ),
        "wins_vs_previous_five_round": sum(
            row["difference_vs_previous_five_round"] > 0 for row in runs
        ),
        "offline_pretrained_scoring_seconds": offline_scoring,
        "metric": "official Spider exact match",
        "timing_boundary": (
            "End-to-end time includes shared pretrained pool scoring, online "
            "selection and reward updates, cumulative training, generation, and "
            "official exact-match evaluation."
        ),
        "method_boundary": (
            "Five-round Spider adaptation with training-time first-order gradient "
            "utility, loss-quantile difficulty clusters, database task groups, "
            "EXP3 allocation, and cumulative replay. This is a transparent "
            "task-specific adaptation rather than an exact reproduction of the "
            "original causal-language-model implementation."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
