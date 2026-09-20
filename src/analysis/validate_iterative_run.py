#!/usr/bin/env python3
"""Validate numerical and budget invariants for one iterative run."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()

    summary = json.loads(
        (args.run_dir / "experiment_summary.json").read_text(encoding="utf-8")
    )
    rounds = summary["round_summaries"]
    if sum(item["selected_samples"] for item in rounds) != summary["total_budget"]:
        raise ValueError("selected sample count does not match the total budget")
    expected_steps = summary.get("total_training_steps")
    if expected_steps is not None:
        actual_steps = sum(item["training_step_budget"] for item in rounds)
        if actual_steps != expected_steps:
            raise ValueError("round training steps do not match total-training-steps")
    if summary.get("training_mode") == "cumulative_union":
        expected_sizes = []
        running = 0
        for item in rounds:
            running += item["selected_samples"]
            expected_sizes.append(running)
        actual_sizes = [item["training_samples"] for item in rounds]
        if actual_sizes != expected_sizes:
            raise ValueError("cumulative training data did not grow as expected")
    if any(item["mean_selected_idu_proxy"] < 0 for item in rounds):
        raise ValueError("negative IDU proxy remains after applying the loss boundary")
    for item in rounds:
        reward = float(item["raw_idu_reduction_reward"])
        bounded_reward = float(item["bounded_exp3_reward"])
        if not math.isfinite(reward) or not math.isfinite(bounded_reward):
            raise ValueError("non-finite MAB reward found")
        if not -1.0 <= bounded_reward <= 1.0:
            raise ValueError("bounded EXP3 reward is outside [-1, 1]")
    selected_rows = []
    with (args.run_dir / "selected_all.jsonl").open(encoding="utf-8") as handle:
        selected_rows = [json.loads(line) for line in handle if line.strip()]
    selected_ids = [row["id"] for row in selected_rows]
    if len(selected_ids) != summary["total_budget"]:
        raise ValueError("selected_all.jsonl does not match the total budget")
    if summary.get("selection_policy") in (
        "gradient_idu",
        "gradient_lead",
        "gradient_lead_replay",
        "gradient_balanced_replay",
    ):
        counts: dict[str, int] = {}
        for selected_id in selected_ids:
            counts[selected_id] = counts.get(selected_id, 0) + 1
        if max(counts.values(), default=0) > int(summary["max_reuse"]):
            raise ValueError("gradient IDU exceeded the configured reuse limit")
        if len(counts) != int(summary["unique_selected_samples"]):
            raise ValueError("gradient IDU unique-sample count is inconsistent")
    elif len(set(selected_ids)) != len(selected_ids):
        raise ValueError("duplicate selected example IDs found")
    if not (args.run_dir / "final_official" / "evaluation.txt").exists():
        raise FileNotFoundError("official exact-match evaluation is missing")
    print("ITERATIVE_RUN_VALIDATED")


if __name__ == "__main__":
    main()
