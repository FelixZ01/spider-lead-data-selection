#!/usr/bin/env python3
"""Show progress and a rough ETA for the iterative LEAD-style pipeline."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "outputs/spider_iterative_lead_1000_pool_500_budget_2_rounds"
RESULT = ROOT / "results/spider_iterative_lead_1000_pool_500_budget_2_rounds"
SEEDS = [11, 42, 73, 101, 202]


def process_running() -> bool:
    if (ROOT / ".cache/iterative_lead_pipeline.lock").exists():
        return True
    pid_path = ROOT / ".cache/iterative_lead_pipeline.pid"
    if not pid_path.exists():
        return False
    try:
        os.kill(int(pid_path.read_text().strip()), 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def main() -> None:
    completed = []
    official = []
    durations = []
    for seed in SEEDS:
        seed_dir = EXPERIMENT / f"seed_{seed}"
        summary_path = seed_dir / "experiment_summary.json"
        if (seed_dir / "COMPLETE").exists() and summary_path.exists():
            completed.append(seed)
            durations.append(float(json.loads(summary_path.read_text())["total_seconds"]))
        if (seed_dir / "final_official/evaluation.txt").exists():
            official.append(seed)

    remaining = len(SEEDS) - len(official)
    average = sum(durations) / len(durations) if durations else 600.0
    eta_seconds = remaining * average
    eta = dt.datetime.now().astimezone() + dt.timedelta(seconds=eta_seconds)
    smoke = (ROOT / "outputs/iterative_lead_smoke_v2_seed42/COMPLETE").exists()
    final = (RESULT / "PIPELINE_COMPLETE").exists()

    print(f"Active: {'yes' if process_running() else 'no'}")
    print(f"Smoke test: {'complete' if smoke else 'pending'}")
    print(f"Model runs complete: {len(completed)}/{len(SEEDS)} {completed}")
    print(f"Official evaluations complete: {len(official)}/{len(SEEDS)} {official}")
    print(f"Final summary: {'complete' if final else 'pending'}")
    if final:
        print(f"Result: {RESULT / 'metrics.json'}")
    elif process_running():
        print(f"Estimated remaining time: {eta_seconds / 60:.1f} minutes")
        print(f"Estimated finish: {eta.strftime('%Y-%m-%d %H:%M:%S %Z')}")


if __name__ == "__main__":
    main()
