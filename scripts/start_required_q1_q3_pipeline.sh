#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

mkdir -p logs
timestamp="$(date '+%Y%m%d_%H%M%S')"
log_file="logs/required_q1_q3_${timestamp}.log"
nohup bash scripts/run_required_q1_q3_pipeline.sh > "$log_file" 2>&1 &
pipeline_pid="$!"

echo "$pipeline_pid" > .cache/required_q1_q3_launcher.pid
echo "Started process $pipeline_pid"
echo "Log: $log_file"
