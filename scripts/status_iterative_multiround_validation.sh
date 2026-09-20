#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

seed="${SEED:-42}"
run_dir="${OUTPUT_DIR:-outputs/spider_iterative_multiround_cumulative/seed_$seed}"

if [[ -f "$run_dir/COMPLETE" ]]; then
  echo "Status: complete"
elif [[ -f .cache/iterative_multiround_validation.pid ]] && \
     kill -0 "$(cat .cache/iterative_multiround_validation.pid)" 2>/dev/null; then
  echo "Status: running"
else
  echo "Status: not running or interrupted"
fi

completed_rounds=0
for round in 1 2 3 4 5; do
  if [[ -f "$run_dir/round_$round/round_summary.json" ]]; then
    completed_rounds=$round
  fi
done
echo "completed_rounds: $completed_rounds/5"

if [[ -f "$run_dir/experiment_summary.json" ]]; then
  echo "Summary: $run_dir/experiment_summary.json"
fi
