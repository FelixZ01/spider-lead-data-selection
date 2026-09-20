#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
seeds="${SEEDS:-11 42 73 101 202}"
experiment_dir="${EXPERIMENT_DIR:-outputs/spider_iterative_multiround_cumulative}"
result_dir="${RESULT_DIR:-results/spider_iterative_multiround_cumulative}"
lock_dir=".cache/iterative_multiround_multiseed.lock"
pid_file=".cache/iterative_multiround_multiseed.pid"

mkdir -p .cache logs "$experiment_dir" "$result_dir"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another multi-seed pipeline appears to be active: $lock_dir" >&2
  exit 1
fi
echo "$$" > "$pid_file"

cleanup() {
  rm -f "$pid_file"
  rmdir "$lock_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Started five-round multi-seed pipeline: $(date)"
echo "Seeds: $seeds"

for seed in $seeds; do
  run_dir="$experiment_dir/seed_$seed"
  if [[ -f "$run_dir/COMPLETE" ]]; then
    echo "=== seed=$seed already complete; validating ==="
    "$python_bin" src/analysis/validate_iterative_run.py --run-dir "$run_dir"
    continue
  fi
  echo "=== running seed=$seed ==="
  SEED="$seed" OUTPUT_DIR="$run_dir" \
    bash scripts/run_iterative_multiround_validation.sh
done

read -r -a seed_array <<< "$seeds"
"$python_bin" src/analysis/summarize_iterative_multiround.py \
  --experiment-dir "$experiment_dir" \
  --required-metrics results/spider_required_q1_q3/metrics.json \
  --scoring-metrics outputs/spider_multiseed_experiment/scoring_metrics.json \
  --seeds "${seed_array[@]}" \
  --output "$result_dir/metrics.json"

touch "$result_dir/PIPELINE_COMPLETE"
echo "Completed five-round multi-seed pipeline: $(date)"
echo "Results: $result_dir/metrics.json"
