#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

experiment_dir="${EXPERIMENT_DIR:-outputs/spider_iterative_multiround_cumulative}"
result_dir="${RESULT_DIR:-results/spider_iterative_multiround_cumulative}"
seeds=(11 42 73 101 202)

if [[ -f "$result_dir/PIPELINE_COMPLETE" ]]; then
  echo "Status: complete"
elif [[ -d .cache/iterative_multiround_multiseed.lock ]]; then
  echo "Status: running or lock present"
else
  echo "Status: not running"
fi

completed=0
for seed in "${seeds[@]}"; do
  if [[ -f "$experiment_dir/seed_$seed/COMPLETE" ]]; then
    echo "seed_$seed: complete"
    completed=$((completed + 1))
  else
    round_count=0
    for round in 1 2 3 4 5; do
      [[ -f "$experiment_dir/seed_$seed/round_$round/round_summary.json" ]] && round_count=$round
    done
    echo "seed_$seed: $round_count/5 rounds"
  fi
done
echo "completed_seeds: $completed/5"
