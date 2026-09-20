#!/usr/bin/env python3
"""Summarise five-round cumulative iterative runs against required controls."""

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
    parser.add_argument("--required-metrics", required=True, type=Path)
    parser.add_argument("--scoring-metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    args = parser.parse_args()

    required = read_json(args.required_metrics)
    offline_scoring = float(read_json(args.scoring_metrics)["scoring_seconds"])
    controls = {
        method: {
            int(row["seed"]): row
            for row in required["methods"][method]["runs"]
        }
        for method in ("full_data", "random", "iterative_lead")
    }

    runs = []
    for seed in args.seeds:
        run_dir = args.experiment_dir / f"seed_{seed}"
        summary = read_json(run_dir / "experiment_summary.json")
        timings = summary["stage_timings"]
        score = official_exact(run_dir / "final_official" / "evaluation.txt")
        random_score = float(controls["random"][seed]["official_spider_exact_match"])
        two_round_score = float(
            controls["iterative_lead"][seed]["official_spider_exact_match"]
        )
        full_score = float(controls["full_data"][seed]["official_spider_exact_match"])
        runs.append({
            "seed": seed,
            "official_spider_exact_match": score,
            "random_exact_match": random_score,
            "two_round_iterative_exact_match": two_round_score,
            "full_data_exact_match": full_score,
            "difference_vs_random": score - random_score,
            "difference_vs_two_round_iterative": score - two_round_score,
            "difference_vs_full_data": score - full_score,
            "selected_databases": summary["selected_databases_total"],
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
        })

    numeric_keys = (
        "official_spider_exact_match",
        "difference_vs_random",
        "difference_vs_two_round_iterative",
        "difference_vs_full_data",
        "selected_databases",
        "selection_or_scoring_seconds",
        "training_seconds",
        "evaluation_seconds",
        "end_to_end_seconds",
    )
    result = {
        "question": (
            "Does a five-round cumulative-training adaptation improve the simplified "
            "iterative method under the same 500-example and 1,500-step budget?"
        ),
        "controlled_setup": {
            "model": "Salesforce/codet5-small",
            "candidate_pool": 1000,
            "selected_budget": 500,
            "selection_rounds": 5,
            "budget_per_round": 100,
            "training_mode": "cumulative_union",
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
        "wins_vs_two_round_iterative": sum(
            row["difference_vs_two_round_iterative"] > 0 for row in runs
        ),
        "offline_pretrained_scoring_seconds": offline_scoring,
        "metric": "official Spider exact match",
        "timing_boundary": (
            "End-to-end time includes the shared pretrained pool scoring, online "
            "rescoring and selection, cumulative training, generation, and official "
            "exact-match evaluation."
        ),
        "method_boundary": (
            "Five-round observed-loss-change adaptation with cumulative training, "
            "a fixed 1,500-step budget, loss-quantile difficulty clusters, "
            "database-level task groups, and EXP3 scheduling. It is not the paper's "
            "inference-free gradient implementation."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
