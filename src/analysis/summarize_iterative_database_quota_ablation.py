#!/usr/bin/env python3
"""Summarise the IDU plus database-quota component ablation."""

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


def by_seed(metrics: dict) -> dict[int, dict]:
    return {int(row["seed"]): row for row in metrics["runs"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-dir", required=True, type=Path)
    parser.add_argument("--required-metrics", required=True, type=Path)
    parser.add_argument("--idu-metrics", required=True, type=Path)
    parser.add_argument("--cluster-mab-metrics", required=True, type=Path)
    parser.add_argument("--full-adaptation-metrics", required=True, type=Path)
    parser.add_argument("--scoring-metrics", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    args = parser.parse_args()

    required = read_json(args.required_metrics)
    idu = by_seed(read_json(args.idu_metrics))
    cluster_mab = by_seed(read_json(args.cluster_mab_metrics))
    full_adaptation = by_seed(read_json(args.full_adaptation_metrics))
    offline_scoring = float(read_json(args.scoring_metrics)["scoring_seconds"])
    random_runs = {
        int(row["seed"]): row
        for row in required["methods"]["random"]["runs"]
    }
    full_runs = {
        int(row["seed"]): row
        for row in required["methods"]["full_data"]["runs"]
    }

    runs = []
    for seed in args.seeds:
        run_dir = args.experiment_dir / f"seed_{seed}"
        summary = read_json(run_dir / "experiment_summary.json")
        if summary.get("selection_policy") != "task_idu":
            raise ValueError(f"seed {seed} is not a database-quota ablation")
        timings = summary["stage_timings"]
        score = official_exact(run_dir / "final_official" / "evaluation.txt")
        comparisons = {
            "idu_only": float(idu[seed]["official_spider_exact_match"]),
            "cluster_mab_only": float(cluster_mab[seed]["official_spider_exact_match"]),
            "full_adaptation": float(full_adaptation[seed]["official_spider_exact_match"]),
            "random": float(random_runs[seed]["official_spider_exact_match"]),
            "full_data": float(full_runs[seed]["official_spider_exact_match"]),
        }
        row = {
            "seed": seed,
            "official_spider_exact_match": score,
            **{f"{name}_exact_match": value for name, value in comparisons.items()},
            **{f"difference_vs_{name}": score - value for name, value in comparisons.items()},
            "selected_databases": summary["selected_databases_total"],
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
        runs.append(row)

    numeric_keys = (
        "official_spider_exact_match",
        "difference_vs_idu_only",
        "difference_vs_cluster_mab_only",
        "difference_vs_full_adaptation",
        "difference_vs_random",
        "difference_vs_full_data",
        "selected_databases",
        "selection_or_scoring_seconds",
        "training_seconds",
        "evaluation_seconds",
        "end_to_end_seconds",
    )
    result = {
        "question": (
            "Does proportional database-group allocation improve five-round IDU "
            "selection when difficulty clustering and EXP3 are removed?"
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
        "wins_vs_idu_only": sum(row["difference_vs_idu_only"] > 0 for row in runs),
        "wins_vs_cluster_mab_only": sum(
            row["difference_vs_cluster_mab_only"] > 0 for row in runs
        ),
        "wins_vs_full_adaptation": sum(
            row["difference_vs_full_adaptation"] > 0 for row in runs
        ),
        "wins_vs_random": sum(row["difference_vs_random"] > 0 for row in runs),
        "offline_pretrained_scoring_seconds": offline_scoring,
        "metric": "official Spider exact match",
        "timing_boundary": (
            "End-to-end time includes shared pretrained pool scoring, online "
            "rescoring and selection, cumulative training, generation, and official "
            "exact-match evaluation."
        ),
        "method_boundary": (
            "Five-round observed-loss-change utility with proportional database-group "
            "allocation over all remaining samples. Difficulty clustering and EXP3 "
            "allocation are removed; all other controlled settings match the full "
            "five-round adaptation."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
