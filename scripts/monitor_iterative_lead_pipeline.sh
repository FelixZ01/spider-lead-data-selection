#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

interval="${CHECK_INTERVAL_SECONDS:-300}"
watch_mode="${1:-once}"

show_status() {
  echo "=== $(date) ==="
  .venv/bin/python src/analysis/iterative_pipeline_status.py
  latest_log="$(ls -t logs/iterative_lead_*.log 2>/dev/null | head -1 || true)"
  if [[ -n "$latest_log" ]]; then
    echo "Latest log: $latest_log"
    tail -n 8 "$latest_log"
  fi
}

show_status
if [[ "$watch_mode" == "--watch" ]]; then
  while [[ ! -f results/spider_iterative_lead_1000_pool_500_budget_2_rounds/PIPELINE_COMPLETE ]]; do
    sleep "$interval"
    show_status
    pid_file=".cache/iterative_lead_pipeline.pid"
    if [[ ! -f "$pid_file" ]] || ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      echo "Pipeline stopped before the completion marker was created." >&2
      exit 1
    fi
  done
fi
