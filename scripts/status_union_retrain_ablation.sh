#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ -f results/spider_iterative_union_retrain/PIPELINE_COMPLETE ]]; then
  echo "Status: complete"
else
  echo "Status: running or not started"
fi

count="$(find outputs/spider_iterative_union_retrain -name COMPLETE 2>/dev/null | wc -l | tr -d ' ')"
echo "fresh_union_retrain: $count/5"

latest_log="$(ls -t logs/union_retrain_ablation_*.log 2>/dev/null | head -1 || true)"
if [[ -n "$latest_log" ]]; then
  echo "Log: $latest_log"
  tail -20 "$latest_log"
fi
