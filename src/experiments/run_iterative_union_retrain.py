#!/usr/bin/env python3
"""Retrain a fresh model on the union selected by an iterative Spider run."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run(command: list[str], extra_env: dict[str, str] | None = None) -> float:
    print("+", " ".join(command), flush=True)
    environment = os.environ.copy()
    environment.setdefault("HF_HOME", str(PROJECT_ROOT / ".cache" / "huggingface"))
    environment.setdefault("HF_HUB_OFFLINE", "1")
    environment.setdefault("TRANSFORMERS_OFFLINE", "1")
    environment.setdefault("TOKENIZERS_PARALLELISM", "false")
    environment.setdefault("NLTK_DATA", str(PROJECT_ROOT / ".cache" / "nltk"))
    if extra_env:
        environment.update(extra_env)
    started = time.perf_counter()
    subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=True)
    return time.perf_counter() - started


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-dir", required=True, type=Path)
    parser.add_argument("--eval-file", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--base-model", default="Salesforce/codet5-small")
    parser.add_argument("--budget", type=int, default=500)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if (args.output_dir / "COMPLETE").exists():
        print(f"Already complete: {args.output_dir}")
        return

    source = args.selection_dir / "selected_all.jsonl"
    selected = read_jsonl(source)
    if len(selected) != args.budget:
        raise ValueError(f"Expected {args.budget} selected rows, found {len(selected)}")
    ids = [row["id"] for row in selected]
    if len(set(ids)) != len(ids):
        raise ValueError("Iterative selection contains duplicate example IDs")

    selected_path = args.output_dir / "selected_union.jsonl"
    if not selected_path.exists():
        write_jsonl(selected, selected_path)

    timings_path = args.output_dir / "stage_timings.json"
    if timings_path.exists():
        timings = json.loads(timings_path.read_text(encoding="utf-8"))
    else:
        timings = {
            "fresh_training_seconds": 0.0,
            "evaluation_seconds": 0.0,
            "official_evaluation_seconds": 0.0,
        }

    model_dir = args.output_dir / "model"
    if not (model_dir / "train_metrics.json").exists():
        timings["fresh_training_seconds"] = run([
            sys.executable,
            "src/training/train_codet5.py",
            "--train-file", str(selected_path),
            "--output-dir", str(model_dir),
            "--model", args.base_model,
            "--max-samples", str(args.budget),
            "--sample-strategy", "head",
            "--epochs", str(args.epochs),
            "--seed", str(args.seed),
            "--device", args.device,
            "--log-every", "100",
        ])
        timings_path.write_text(json.dumps(timings, indent=2) + "\n", encoding="utf-8")

    eval_dir = args.output_dir / "eval"
    if not (eval_dir / "eval_metrics.json").exists():
        timings["evaluation_seconds"] = run([
            sys.executable,
            "src/eval/evaluate_codet5.py",
            "--model-dir", str(model_dir),
            "--eval-file", str(args.eval_file),
            "--output-dir", str(eval_dir),
            "--max-samples", "1034",
            "--sample-strategy", "head",
            "--seed", "2026",
            "--device", args.device,
            "--quiet",
        ])
        timings_path.write_text(json.dumps(timings, indent=2) + "\n", encoding="utf-8")

    official_dir = args.output_dir / "official"
    if not (official_dir / "evaluation.txt").exists():
        timings["official_evaluation_seconds"] = run(
            ["bash", "scripts/run_official_spider_eval.sh", "iterative_union_retrain", "match"],
            {
                "PREDICTION_JSONL": str(eval_dir / "predictions.jsonl"),
                "OFFICIAL_OUTPUT_DIR": str(official_dir),
            },
        )
        timings_path.write_text(json.dumps(timings, indent=2) + "\n", encoding="utf-8")

    summary = {
        "method": "iterative_selection_fresh_union_retrain",
        "purpose": (
            "Isolate selected-data quality from sequential-training effects by "
            "retraining a fresh model on the union of both selected rounds."
        ),
        "selection_source": str(source),
        "base_model": args.base_model,
        "selected_samples": len(selected),
        "selected_databases": len({row["db_id"] for row in selected}),
        "epochs": args.epochs,
        "seed": args.seed,
        "timings": timings,
        "retrain_and_evaluate_seconds": sum(timings.values()),
        "timing_boundary": (
            "Diagnostic retraining and evaluation only; the earlier iterative "
            "selection cost is intentionally reported separately."
        ),
    }
    (args.output_dir / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "COMPLETE").touch()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
