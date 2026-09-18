#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

mkdir -p logs .cache
pid_file=".cache/unattended_pipeline.pid"

if [[ -f "$pid_file" ]]; then
  existing_pid="$(cat "$pid_file")"
  if kill -0 "$existing_pid" 2>/dev/null; then
    echo "The unattended pipeline is already running with PID $existing_pid."
    exit 0
  fi
fi

launcher_log="logs/unattended_launcher_$(date '+%Y%m%d_%H%M%S').log"
nohup bash scripts/run_unattended_mac_pipeline.sh > "$launcher_log" 2>&1 &
pipeline_pid="$!"
echo "$pipeline_pid" > "$pid_file"
sleep 1

if kill -0 "$pipeline_pid" 2>/dev/null; then
  echo "Unattended pipeline started successfully."
  echo "PID: $pipeline_pid"
  echo "Launcher log: $launcher_log"
  echo "Monitor with: bash scripts/monitor_unattended_pipeline.sh"
else
  echo "The unattended pipeline failed to start." >&2
  tail -n 30 "$launcher_log" >&2
  exit 1
fi
