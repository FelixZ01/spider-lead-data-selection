#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ -f results/spider_required_q1_q3/PIPELINE_COMPLETE ]]; then
  echo "Status: complete"
elif [[ -d .cache/required_q1_q3_pipeline.lock ]]; then
  echo "Status: running"
else
  echo "Status: not running"
fi

for method in full_data random; do
  count="$(find outputs/spider_required_q1_q3_baselines -path "*/$method/COMPLETE" 2>/dev/null | wc -l | tr -d ' ')"
  echo "$method: $count/5"
done
iterative_count="$(find outputs/spider_required_q1_q3_iterative -name COMPLETE 2>/dev/null | wc -l | tr -d ' ')"
echo "iterative_lead: $iterative_count/5"

latest_log="$(ls -t logs/required_q1_q3_*.log 2>/dev/null | head -1 || true)"
if [[ -n "$latest_log" ]]; then
  echo "Log: $latest_log"
  tail -20 "$latest_log"
fi
