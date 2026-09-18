#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

while true; do
  clear
  date
  echo "=== Unattended Spider Pipeline Monitor (refreshes every 5 seconds) ==="
  process_ids="$(pgrep -f 'run_unattended_mac_pipeline.sh|train_codet5.py|evaluate_codet5.py' | tr '\n' ',' | sed 's/,$//' || true)"
  if [[ -n "$process_ids" ]]; then
    ps -p "$process_ids" -o pid,etime,%cpu,%mem,command
  else
    echo "No active experiment process detected."
  fi
  echo
  completed="$(find outputs/spider_scaled_multiseed_experiment \
    -path '*full_dev_official/evaluation.txt' -type f | wc -l | tr -d ' ')"
  echo "Completed full-development evaluations: $completed"
  latest_log="$(find logs -name 'unattended_*.log' -type f -print | sort | tail -n 1)"
  if [[ -n "$latest_log" ]]; then
    echo "Latest log: $latest_log"
    echo "--- Last 12 log lines ---"
    tail -n 12 "$latest_log"
  fi
  sleep 5
done
