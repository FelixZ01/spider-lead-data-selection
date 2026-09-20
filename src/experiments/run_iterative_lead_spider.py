#!/usr/bin/env python3
"""Run a resumable multi-round LEAD-style data-selection experiment on Spider."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.selection.iterative_lead import (  # noqa: E402
    allocate_evenly,
    assign_quantile_clusters,
    choose_arm,
    exp3_probabilities,
    observed_idu_proxy,
    proportional_task_select,
    update_exp3,
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run(command: list[str], extra_env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    environment = os.environ.copy()
    environment.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))
    environment.setdefault("HF_HUB_OFFLINE", "1")
    environment.setdefault("TRANSFORMERS_OFFLINE", "1")
    environment.setdefault("TOKENIZERS_PARALLELISM", "false")
    environment.setdefault("NLTK_DATA", str(PROJECT_ROOT / ".cache" / "nltk"))
    if extra_env:
        environment.update(extra_env)
    subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=True)


def score_rows(input_file: Path, output_file: Path, model: str, device: str) -> list[dict[str, Any]]:
    run([
        sys.executable,
        "src/selection/score_codet5_model_loss.py",
        "--input", str(input_file),
        "--output", str(output_file),
        "--model", model,
        "--score-key", "current_target_loss",
        "--device", device,
    ])
    return read_jsonl(output_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-file", required=True, type=Path)
    parser.add_argument("--eval-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--base-model", default="Salesforce/codet5-small")
    parser.add_argument("--pool-size", type=int, default=1000)
    parser.add_argument("--budget", type=int, default=500)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--clusters", type=int, default=2)
    parser.add_argument("--epochs-per-round", type=int, default=3)
    parser.add_argument(
        "--training-mode",
        choices=("new_batch", "cumulative_union"),
        default="new_batch",
        help="Train each round on only its new batch or all samples selected so far.",
    )
    parser.add_argument(
        "--total-training-steps",
        type=int,
        default=None,
        help="Optional fixed optimizer-step budget divided across all rounds.",
    )
    parser.add_argument("--eval-samples", type=int, default=1034)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoothing", type=float, default=0.1)
    parser.add_argument("--gamma", type=float, default=0.06)
    parser.add_argument(
        "--selection-policy",
        choices=(
            "exp3_cluster_task",
            "exp3_cluster_global",
            "task_idu",
            "global_idu",
            "static_uncertainty",
        ),
        default="exp3_cluster_task",
        help=(
            "Use the clustering/EXP3 adaptation with or without database-group "
            "allocation, apply database-group allocation directly to current "
            "IDU scores, select the highest current IDU proxies globally, or "
            "keep the initial pretrained-loss ranking fixed across rounds."
        ),
    )
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        if (args.output_dir / "COMPLETE").exists():
            print(f"Already complete: {args.output_dir}")
            return
        raise RuntimeError(f"Incomplete non-empty output directory: {args.output_dir}")
    if args.budget % args.rounds:
        raise ValueError("budget must be divisible by rounds")
    batch_budget = args.budget // args.rounds
    if args.total_training_steps is not None and args.total_training_steps < args.rounds:
        raise ValueError("total-training-steps must be at least the number of rounds")
    round_step_budgets = (
        allocate_evenly(args.total_training_steps, args.rounds)
        if args.total_training_steps is not None
        else [None] * args.rounds
    )
    rows = read_jsonl(args.pool_file)[: args.pool_size]
    if len(rows) < args.pool_size:
        raise ValueError("pool file contains fewer rows than pool-size")
    if args.budget > len(rows):
        raise ValueError("budget cannot exceed pool-size")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    rng = random.Random(args.seed)
    cluster_by_id = assign_quantile_clusters(rows, args.clusters, "pretrained_target_loss")
    state: dict[str, dict[str, float]] = {
        row["id"]: {
            "previous_loss": float(row["pretrained_target_loss"]),
            "previous_utility": float(row["pretrained_target_loss"]),
        }
        for row in rows
    }
    remaining = [dict(row, difficulty_cluster=cluster_by_id[row["id"]]) for row in rows]
    selected_all: list[dict[str, Any]] = []
    selected_training_rows: list[dict[str, Any]] = []
    weights = [1.0] * args.clusters
    reward_history: list[float] = []
    round_summaries: list[dict[str, Any]] = []
    current_model = args.base_model
    stage_timings = {
        "online_selection_seconds": 0.0,
        "training_wall_seconds": 0.0,
        "reward_update_seconds": 0.0,
        "evaluation_wall_seconds": 0.0,
        "official_evaluation_seconds": 0.0,
    }

    for round_index in range(1, args.rounds + 1):
        selection_started = time.perf_counter()
        round_dir = args.output_dir / f"round_{round_index}"
        round_dir.mkdir(parents=True, exist_ok=True)
        remaining_input = round_dir / "remaining_input.jsonl"
        write_jsonl(remaining, remaining_input)

        if round_index == 1 or args.selection_policy == "static_uncertainty":
            scored_remaining = []
            for row in remaining:
                copied = dict(row)
                copied["current_target_loss"] = float(row["pretrained_target_loss"])
                copied["idu_proxy"] = float(row["pretrained_target_loss"])
                scored_remaining.append(copied)
        else:
            scored_remaining = score_rows(
                remaining_input,
                round_dir / "remaining_scored.jsonl",
                current_model,
                args.device,
            )
            for row in scored_remaining:
                previous = state[row["id"]]
                row["idu_proxy"] = observed_idu_proxy(
                    float(row["current_target_loss"]),
                    previous["previous_loss"],
                    previous["previous_utility"],
                    args.smoothing,
                )

        counts = Counter(int(row["difficulty_cluster"]) for row in scored_remaining)
        probabilities: list[float] | None = None
        arm: int | None = None
        if args.selection_policy in ("exp3_cluster_task", "exp3_cluster_global"):
            probabilities = exp3_probabilities(weights, args.gamma)
            eligible = [counts[index] >= batch_budget for index in range(args.clusters)]
            arm = choose_arm(probabilities, eligible, rng)
            candidates = [
                row
                for row in scored_remaining
                if int(row["difficulty_cluster"]) == arm
            ]
            if args.selection_policy == "exp3_cluster_task":
                selected = proportional_task_select(
                    candidates, batch_budget, "idu_proxy"
                )
            else:
                selected = sorted(
                    candidates,
                    key=lambda row: (-float(row["idu_proxy"]), row["id"]),
                )[:batch_budget]
        elif args.selection_policy == "task_idu":
            selected = proportional_task_select(
                scored_remaining, batch_budget, "idu_proxy"
            )
        else:
            selected = sorted(
                scored_remaining,
                key=lambda row: (-float(row["idu_proxy"]), row["id"]),
            )[:batch_budget]
        selected_ids = {row["id"] for row in selected}
        selected_path = round_dir / "selected.jsonl"
        write_jsonl(selected, selected_path)
        selected_training_rows.extend(selected)
        training_rows = (
            selected if args.training_mode == "new_batch" else selected_training_rows
        )
        training_path = round_dir / "training_data.jsonl"
        write_jsonl(training_rows, training_path)
        stage_timings["online_selection_seconds"] += (
            time.perf_counter() - selection_started
        )

        model_dir = round_dir / "model"
        training_started = time.perf_counter()
        training_command = [
            sys.executable,
            "src/training/train_codet5.py",
            "--train-file", str(training_path),
            "--output-dir", str(model_dir),
            "--model", current_model,
            "--max-samples", str(len(training_rows)),
            "--sample-strategy", "head",
            "--epochs", str(args.epochs_per_round),
            "--seed", str(args.seed),
            "--device", args.device,
            "--log-every", "100",
        ]
        round_step_budget = round_step_budgets[round_index - 1]
        if round_step_budget is not None:
            training_command.extend(["--max-steps", str(round_step_budget)])
        run(training_command)
        stage_timings["training_wall_seconds"] += (
            time.perf_counter() - training_started
        )

        reward_started = time.perf_counter()
        if args.selection_policy == "static_uncertainty":
            after_by_id: dict[str, dict[str, Any]] = {}
        else:
            after_rows = score_rows(
                selected_path,
                round_dir / "selected_after_training.jsonl",
                str(model_dir),
                args.device,
            )
            after_by_id = {row["id"]: row for row in after_rows}
        reductions: list[float] = []
        for row in selected:
            before_loss = float(row["current_target_loss"])
            before_utility = float(row["idu_proxy"])
            if args.selection_policy == "static_uncertainty":
                after_loss = None
                after_utility = None
                reductions.append(0.0)
            else:
                after_loss = float(after_by_id[row["id"]]["current_target_loss"])
                after_utility = observed_idu_proxy(
                    after_loss, before_loss, before_utility, args.smoothing
                )
                reductions.append(before_utility - after_utility)
            enriched = dict(row)
            enriched["after_training_target_loss"] = after_loss
            enriched["after_training_idu_proxy"] = after_utility
            enriched["round_selected"] = round_index
            selected_all.append(enriched)

        raw_reward = sum(reductions) / len(reductions)
        scale = max(
            1e-8,
            sum(abs(float(row["idu_proxy"])) for row in selected) / len(selected),
        )
        bounded_reward = math.tanh(raw_reward / scale)
        if args.selection_policy in ("exp3_cluster_task", "exp3_cluster_global"):
            if arm is None or probabilities is None:
                raise RuntimeError("EXP3 state was not initialised")
            weights = update_exp3(
                weights, arm, bounded_reward, probabilities[arm], args.gamma
            )
        reward_history.append(raw_reward)

        next_remaining: list[dict[str, Any]] = []
        for row in scored_remaining:
            if row["id"] in selected_ids:
                continue
            state[row["id"]] = {
                "previous_loss": float(row["current_target_loss"]),
                "previous_utility": float(row["idu_proxy"]),
            }
            next_remaining.append(row)
        remaining = next_remaining
        current_model = str(model_dir)

        round_summary = {
            "round": round_index,
            "selected_samples": len(selected),
            "training_samples": len(training_rows),
            "training_step_budget": round_step_budget,
            "selected_databases": len({row["db_id"] for row in selected}),
            "selected_difficulty_cluster": arm,
            "cluster_counts_before_selection": dict(sorted(counts.items())),
            "mab_probabilities_before_selection": probabilities,
            "mab_weights_after_update": (
                weights
                if args.selection_policy in (
                    "exp3_cluster_task",
                    "exp3_cluster_global",
                )
                else None
            ),
            "raw_idu_reduction_reward": raw_reward,
            "bounded_exp3_reward": bounded_reward,
            "mean_selected_idu_proxy": sum(float(row["idu_proxy"]) for row in selected) / len(selected),
            "mean_selected_loss_before": sum(float(row["current_target_loss"]) for row in selected) / len(selected),
            "mean_selected_loss_after": (
                None
                if args.selection_policy == "static_uncertainty"
                else sum(
                    float(after_by_id[row["id"]]["current_target_loss"])
                    for row in selected
                ) / len(selected)
            ),
        }
        round_summaries.append(round_summary)
        (round_dir / "round_summary.json").write_text(
            json.dumps(round_summary, indent=2) + "\n", encoding="utf-8"
        )
        write_jsonl(selected_all, args.output_dir / "selected_all.jsonl")
        stage_timings["reward_update_seconds"] += (
            time.perf_counter() - reward_started
        )

    eval_dir = args.output_dir / "final_eval"
    evaluation_started = time.perf_counter()
    run([
        sys.executable,
        "src/eval/evaluate_codet5.py",
        "--model-dir", current_model,
        "--eval-file", str(args.eval_file),
        "--output-dir", str(eval_dir),
        "--max-samples", str(args.eval_samples),
        "--sample-strategy", "head",
        "--seed", "2026",
        "--device", args.device,
        "--quiet",
    ])
    stage_timings["evaluation_wall_seconds"] = (
        time.perf_counter() - evaluation_started
    )

    official_dir = args.output_dir / "final_official"
    official_started = time.perf_counter()
    run(
        [
            "bash",
            "scripts/run_official_spider_eval.sh",
            "iterative_lead",
            "match",
        ],
        {
            "PREDICTION_JSONL": str(eval_dir / "predictions.jsonl"),
            "OFFICIAL_OUTPUT_DIR": str(official_dir),
        },
    )
    stage_timings["official_evaluation_seconds"] = (
        time.perf_counter() - official_started
    )

    summary = {
        "method": {
            "exp3_cluster_task": "simplified_iterative_lead",
            "exp3_cluster_global": "iterative_idu_cluster_mab",
            "task_idu": "iterative_idu_database_quota",
            "global_idu": "iterative_idu_only",
            "static_uncertainty": "static_uncertainty_multiround_control",
        }[args.selection_policy],
        "scope_note": (
            (
                "Observed-loss-change proxy for IDU; loss-quantile difficulty "
                f"clusters; Spider database IDs as task groups; {args.rounds}-round "
                "EXP3 scheduling."
                if args.selection_policy == "exp3_cluster_task"
                else (
                    "Observed-loss-change proxy for IDU with loss-quantile "
                    f"clusters and {args.rounds}-round EXP3 scheduling; selection "
                    "within the chosen cluster is global top utility, so "
                    "database-group allocation is removed."
                    if args.selection_policy == "exp3_cluster_global"
                    else (
                        "Observed-loss-change proxy for IDU with proportional "
                        "database-group allocation over all remaining samples; "
                        f"difficulty clustering and {args.rounds}-round EXP3 "
                        "scheduling are removed."
                        if args.selection_policy == "task_idu"
                        else (
                            "Observed-loss-change proxy for IDU with global top-utility "
                            f"selection over {args.rounds} rounds; clustering, EXP3, and "
                            "database-group allocation are removed for component ablation."
                            if args.selection_policy == "global_idu"
                            else (
                                "The initial pretrained-loss ranking remains fixed over "
                                f"{args.rounds} rounds. No online rescoring or utility "
                                "update is used; the cumulative training schedule matches "
                                "the iterative controls."
                            )
                        )
                    )
                )
            )
            + " This is a transparent adaptation, not a faithful inference-free "
            "LEAD reproduction."
        ),
        "base_model": args.base_model,
        "pool_size": args.pool_size,
        "total_budget": args.budget,
        "rounds": args.rounds,
        "budget_per_round": batch_budget,
        "difficulty_clusters": args.clusters,
        "epochs_per_round": args.epochs_per_round,
        "training_mode": args.training_mode,
        "total_training_steps": args.total_training_steps,
        "round_training_step_budgets": round_step_budgets,
        "seed": args.seed,
        "smoothing": args.smoothing,
        "gamma": args.gamma,
        "selection_policy": args.selection_policy,
        "utility_boundary": "Predicted cross-entropy is clipped at zero.",
        "selected_databases_total": len({row["db_id"] for row in selected_all}),
        "round_summaries": round_summaries,
        "stage_timings": stage_timings,
        "total_seconds": time.perf_counter() - started,
    }
    (args.output_dir / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "COMPLETE").touch()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
