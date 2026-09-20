#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
experiment_dir="${EXPERIMENT_DIR:-outputs/spider_scaled_multiseed_experiment}"
seeds="${SEEDS:-11 42 73 101 202}"
budget="${BUDGET:-500}"
epochs="${EPOCHS:-3}"
eval_samples="${EVAL_SAMPLES:-200}"
result_dir="${RESULT_DIR:-results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs}"
timestamp="$(date '+%Y%m%d_%H%M%S')"
log_file="logs/unattended_${timestamp}.log"
lock_dir=".cache/unattended_pipeline.lock"

mkdir -p logs .cache "$result_dir"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another unattended pipeline appears to be active: $lock_dir" >&2
  exit 1
fi

caffeinate_pid=""
cleanup() {
  if [[ -n "$caffeinate_pid" ]]; then
    kill "$caffeinate_pid" 2>/dev/null || true
  fi
  rmdir "$lock_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

exec >> "$log_file" 2>&1

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu -w "$$" &
  caffeinate_pid="$!"
fi

echo "Started: $(date)"
echo "Project: $project_dir"
echo "Seeds: $seeds"
echo "Log: $log_file"

required_files=(
  "$python_bin"
  "data/processed/spider/dev.jsonl"
  "outputs/spider_multiseed_experiment/scored_pool.jsonl"
)
for required_file in "${required_files[@]}"; do
  if [[ ! -e "$required_file" ]]; then
    echo "Missing required file: $required_file" >&2
    exit 1
  fi
done

echo "=== Step 1/5: tests ==="
"$python_bin" -m unittest discover -s tests -v

echo "=== Step 2/5: train and evaluate missing seeds ==="
SEEDS="$seeds" BUDGET="$budget" EPOCHS="$epochs" EVAL_SAMPLES="$eval_samples" \
  EXPERIMENT_DIR="$experiment_dir" \
  bash scripts/run_mac_scaled_multiseed_experiment.sh

echo "=== Step 3/5: evaluate all missing models on the full development set ==="
for seed in $seeds; do
  SEED="$seed" EXPERIMENT_DIR="$experiment_dir" \
    bash scripts/run_mac_full_dev_eval.sh
done

echo "=== Step 4/5: build machine-readable summaries ==="
read -r -a seed_array <<< "$seeds"
"$python_bin" src/analysis/summarize_multiseed.py \
  --experiment-dir "$experiment_dir" \
  --seeds "${seed_array[@]}" \
  --output "$result_dir/metrics.json"

"$python_bin" src/analysis/summarize_full_dev_multiseed.py \
  --experiment-dir "$experiment_dir" \
  --seeds "${seed_array[@]}" \
  --output "$result_dir/full_dev_multiseed_metrics.json"

echo "=== Step 5/5: build experiment analysis brief ==="
"$python_bin" src/analysis/build_analysis_handoff.py \
  --metrics "$result_dir/full_dev_multiseed_metrics.json" \
  --output "$result_dir/EXPERIMENT_ANALYSIS_BRIEF.md"

touch "$result_dir/LOCAL_EXPERIMENT_COMPLETE"

echo "Completed: $(date)"
echo "Analysis brief: $result_dir/EXPERIMENT_ANALYSIS_BRIEF.md"
echo "Full log: $log_file"
