#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

while true; do
  clear
  .venv/bin/python src/analysis/pipeline_status.py \
    --seeds ${SEEDS:-11 42 73 101 202}
  echo
  latest_log="$(find logs -name 'unattended_*.log' ! -name '*launcher*' -type f -print | sort | tail -n 1)"
  if [[ -n "$latest_log" ]]; then
    echo "Latest log: $latest_log"
    echo "--- Last 12 log lines ---"
    tail -n 12 "$latest_log"
  fi
  sleep 5
done
