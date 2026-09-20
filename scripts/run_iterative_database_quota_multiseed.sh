#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
seeds="${SEEDS:-11 42 73 101 202}"
experiment_dir="${EXPERIMENT_DIR:-outputs/spider_iterative_database_quota}"
result_dir="${RESULT_DIR:-results/spider_iterative_database_quota}"
lock_dir=".cache/iterative_database_quota.lock"
pid_file=".cache/iterative_database_quota.pid"

export HF_HOME="${HF_HOME:-$project_dir/.cache/huggingface}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export NLTK_DATA="${NLTK_DATA:-$project_dir/.cache/nltk}"

mkdir -p .cache logs "$experiment_dir" "$result_dir"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another database-quota pipeline appears to be active: $lock_dir" >&2
  exit 1
fi
echo "$$" > "$pid_file"

caffeinate_pid=""
cleanup() {
  if [[ -n "$caffeinate_pid" ]]; then
    kill "$caffeinate_pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
  rmdir "$lock_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu -w "$$" &
  caffeinate_pid="$!"
fi

echo "Started five-round IDU plus database-quota ablation: $(date)"
echo "Seeds: $seeds"

for seed in $seeds; do
  run_dir="$experiment_dir/seed_$seed"
  if [[ -f "$run_dir/COMPLETE" ]]; then
    echo "=== seed=$seed already complete; validating ==="
    "$python_bin" src/analysis/validate_iterative_run.py --run-dir "$run_dir"
    continue
  fi
  if [[ -d "$run_dir" ]] && [[ -n "$(find "$run_dir" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    echo "Incomplete output exists for seed=$seed: $run_dir" >&2
    echo "Preserving it for inspection; no new run was started." >&2
    exit 1
  fi
  echo "=== running seed=$seed ==="
  "$python_bin" src/experiments/run_iterative_lead_spider.py \
    --pool-file outputs/spider_multiseed_experiment/scored_pool.jsonl \
    --eval-file data/processed/spider/dev.jsonl \
    --output-dir "$run_dir" \
    --pool-size 1000 --budget 500 --rounds 5 --clusters 2 \
    --training-mode cumulative_union --total-training-steps 1500 \
    --epochs-per-round 3 --eval-samples 1034 --seed "$seed" \
    --smoothing 0.1 --gamma 0.06 --selection-policy task_idu
  "$python_bin" src/analysis/validate_iterative_run.py --run-dir "$run_dir"
done

read -r -a seed_array <<< "$seeds"
"$python_bin" src/analysis/summarize_iterative_database_quota_ablation.py \
  --experiment-dir "$experiment_dir" \
  --required-metrics results/spider_required_q1_q3/metrics.json \
  --idu-metrics results/spider_iterative_idu_only/metrics.json \
  --cluster-mab-metrics results/spider_iterative_cluster_mab/metrics.json \
  --full-adaptation-metrics results/spider_iterative_multiround_cumulative/metrics.json \
  --scoring-metrics outputs/spider_multiseed_experiment/scoring_metrics.json \
  --seeds "${seed_array[@]}" \
  --output "$result_dir/metrics.json"

touch "$result_dir/PIPELINE_COMPLETE"
echo "Completed five-round IDU plus database-quota ablation: $(date)"
echo "Results: $result_dir/metrics.json"
