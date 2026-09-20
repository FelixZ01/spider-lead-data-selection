#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

mkdir -p .cache logs
pid_file=".cache/iterative_lead_pipeline.pid"
if [[ -f "$pid_file" ]]; then
  existing_pid="$(cat "$pid_file")"
  if kill -0 "$existing_pid" 2>/dev/null; then
    echo "The iterative pipeline is already running with PID $existing_pid."
    exit 0
  fi
fi

timestamp="$(date '+%Y%m%d_%H%M%S')"
log_file="logs/iterative_lead_${timestamp}.log"
nohup bash scripts/run_iterative_lead_pipeline.sh > "$log_file" 2>&1 &
pipeline_pid="$!"
echo "$pipeline_pid" > "$pid_file"
sleep 1

if kill -0 "$pipeline_pid" 2>/dev/null; then
  echo "Iterative LEAD-style pipeline started."
  echo "PID: $pipeline_pid"
  echo "Log: $log_file"
  echo "Monitor: bash scripts/monitor_iterative_lead_pipeline.sh"
else
  echo "Pipeline failed to start. See $log_file" >&2
  exit 1
fi
