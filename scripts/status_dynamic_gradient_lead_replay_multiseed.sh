#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

result_dir="results/spider_dynamic_gradient_lead_replay"
experiment_dir="outputs/spider_dynamic_gradient_lead_replay"

if [[ -f "$result_dir/PIPELINE_COMPLETE" ]]; then
  echo "COMPLETE"
elif [[ -d .cache/dynamic_gradient_lead_replay_multiseed.lock ]]; then
  echo "RUNNING"
else
  echo "STOPPED_OR_NOT_STARTED"
fi

for seed in 11 42 73 101 202; do
  run_dir="$experiment_dir/seed_$seed"
  if [[ -f "$run_dir/COMPLETE" ]]; then
    echo "seed=$seed complete"
    continue
  fi
  latest_round=0
  for round in 1 2 3 4 5; do
    [[ -d "$run_dir/round_$round" ]] && latest_round="$round"
  done
  echo "seed=$seed latest_round=$latest_round"
done
