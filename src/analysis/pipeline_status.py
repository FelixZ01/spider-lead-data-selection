#!/usr/bin/env python3
"""Report unattended pipeline progress and estimate remaining runtime."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path


METHODS = ("random", "uncertainty", "uncertainty_schema_diverse")
DEFAULT_TRAIN_SECONDS = 260.0
DEFAULT_SUBSET_EVAL_SECONDS = 60.0
DEFAULT_FULL_EVAL_SECONDS = 290.0


def metric_values(paths: list[Path], field: str) -> list[float]:
    values = []
    for path in paths:
        try:
            values.append(float(json.loads(path.read_text(encoding="utf-8"))[field]))
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return values


def mean_or(values: list[float], default: float) -> float:
    return sum(values) / len(values) if values else default


def active_processes() -> str:
    command = (
        "pgrep -f 'run_unattended_mac_pipeline.sh|train_codet5.py|"
        "evaluate_codet5.py|codex exec'"
    )
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    process_ids = ",".join(result.stdout.split())
    if not process_ids:
        return "No active pipeline process detected."
    process_result = subprocess.run(
        ["ps", "-p", process_ids, "-o", "pid,etime,%cpu,%mem,command"],
        text=True,
        capture_output=True,
    )
    return process_result.stdout.strip()


def format_duration(seconds: float) -> str:
    minutes = max(0, round(seconds / 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment-dir",
        type=Path,
        default=Path("outputs/spider_scaled_multiseed_experiment"),
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=[11, 42, 73, 101, 202])
    args = parser.parse_args()

    train_history = metric_values(
        list(args.experiment_dir.glob("seed_*/*/model/train_metrics.json")),
        "train_seconds",
    )
    subset_history = metric_values(
        list(args.experiment_dir.glob("seed_*/*/eval/eval_metrics.json")),
        "generation_seconds",
    )
    full_history = metric_values(
        list(args.experiment_dir.glob("seed_*/*/full_dev_eval/eval_metrics.json")),
        "generation_seconds",
    )
    train_estimate = mean_or(train_history, DEFAULT_TRAIN_SECONDS)
    subset_estimate = mean_or(subset_history, DEFAULT_SUBSET_EVAL_SECONDS)
    full_estimate = mean_or(full_history, DEFAULT_FULL_EVAL_SECONDS)

    train_done = subset_done = full_done = 0
    remaining_seconds = 0.0
    pending = []
    total_runs = len(args.seeds) * len(METHODS)

    for seed in args.seeds:
        for method in METHODS:
            run_dir = args.experiment_dir / f"seed_{seed}" / method
            model_complete = (run_dir / "model" / "train_metrics.json").exists()
            subset_complete = (run_dir / "official" / "evaluation.txt").exists()
            full_complete = (run_dir / "full_dev_official" / "evaluation.txt").exists()

            train_done += int(model_complete)
            subset_done += int(subset_complete)
            full_done += int(full_complete)

            missing = []
            if not model_complete:
                remaining_seconds += train_estimate
                missing.append("train")
            if not subset_complete:
                remaining_seconds += subset_estimate
                missing.append("subset-eval")
            if not full_complete:
                remaining_seconds += full_estimate
                missing.append("full-dev-eval")
            if missing:
                pending.append(f"seed={seed} method={method}: {', '.join(missing)}")

    now = dt.datetime.now().astimezone()
    estimated_finish = now + dt.timedelta(seconds=remaining_seconds)
    print(now.strftime("%Y-%m-%d %H:%M:%S %Z"))
    print("=== Unattended Spider Pipeline Status ===")
    print(active_processes())
    print()
    print(f"Model training:       {train_done:2d} / {total_runs}")
    print(f"Subset evaluation:    {subset_done:2d} / {total_runs}")
    print(f"Full-dev evaluation:  {full_done:2d} / {total_runs}")
    if pending:
        print(f"Estimated remaining:  {format_duration(remaining_seconds)}")
        print(f"Estimated finish:     {estimated_finish.strftime('%Y-%m-%d %H:%M %Z')}")
        print()
        print("Next pending work:")
        for item in pending[:6]:
            print(f"- {item}")
        if len(pending) > 6:
            print(f"- ... and {len(pending) - 6} more runs")
    else:
        print("Estimated remaining:  complete")


if __name__ == "__main__":
    main()
