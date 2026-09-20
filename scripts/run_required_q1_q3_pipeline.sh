#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
seeds="${SEEDS:-11 42 73 101 202}"
pool_file="outputs/spider_multiseed_experiment/scored_pool.jsonl"
eval_file="data/processed/spider/dev.jsonl"
baseline_dir="${BASELINE_DIR:-outputs/spider_required_q1_q3_baselines}"
iterative_dir="${ITERATIVE_DIR:-outputs/spider_required_q1_q3_iterative}"
result_dir="${RESULT_DIR:-results/spider_required_q1_q3}"
lock_dir=".cache/required_q1_q3_pipeline.lock"
pid_file=".cache/required_q1_q3_pipeline.pid"

export HF_HOME="${HF_HOME:-$project_dir/.cache/huggingface}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export NLTK_DATA="${NLTK_DATA:-$project_dir/.cache/nltk}"

mkdir -p .cache logs "$baseline_dir" "$iterative_dir" "$result_dir"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another required-comparison pipeline appears to be active: $lock_dir" >&2
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

echo "Started: $(date)"
echo "Seeds: $seeds"

echo "=== Stage 1/6: tests ==="
"$python_bin" -m unittest discover -s tests -v

echo "=== Stage 2/6: corrected iterative smoke test ==="
smoke_dir="outputs/spider_required_q1_q3_smoke"
"$python_bin" src/experiments/run_iterative_lead_spider.py \
  --pool-file "$pool_file" \
  --eval-file "$eval_file" \
  --output-dir "$smoke_dir" \
  --pool-size 120 --budget 40 --rounds 2 --clusters 2 \
  --epochs-per-round 1 --eval-samples 50 --seed 42 \
  --smoothing 0.1 --gamma 0.06
"$python_bin" src/analysis/validate_iterative_run.py --run-dir "$smoke_dir"

echo "=== Stage 3/6: full-data and random baselines ==="
for seed in $seeds; do
  for method in full_data random; do
    echo "--- method=$method seed=$seed ---"
    "$python_bin" src/experiments/run_required_baseline.py \
      --method "$method" \
      --pool-file "$pool_file" \
      --eval-file "$eval_file" \
      --output-dir "$baseline_dir/seed_$seed/$method" \
      --pool-size 1000 --budget 500 --epochs 3 --seed "$seed"
  done
done

echo "=== Stage 4/6: one-seed iterative validation ==="
validation_dir="$iterative_dir/seed_42"
"$python_bin" src/experiments/run_iterative_lead_spider.py \
  --pool-file "$pool_file" \
  --eval-file "$eval_file" \
  --output-dir "$validation_dir" \
  --pool-size 1000 --budget 500 --rounds 2 --clusters 2 \
  --epochs-per-round 3 --eval-samples 1034 --seed 42 \
  --smoothing 0.1 --gamma 0.06
"$python_bin" src/analysis/validate_iterative_run.py --run-dir "$validation_dir"

echo "=== Stage 5/6: remaining iterative seeds ==="
for seed in $seeds; do
  run_dir="$iterative_dir/seed_$seed"
  "$python_bin" src/experiments/run_iterative_lead_spider.py \
    --pool-file "$pool_file" \
    --eval-file "$eval_file" \
    --output-dir "$run_dir" \
    --pool-size 1000 --budget 500 --rounds 2 --clusters 2 \
    --epochs-per-round 3 --eval-samples 1034 --seed "$seed" \
    --smoothing 0.1 --gamma 0.06
  "$python_bin" src/analysis/validate_iterative_run.py --run-dir "$run_dir"
done

echo "=== Stage 6/6: required comparison summary ==="
read -r -a seed_array <<< "$seeds"
"$python_bin" src/analysis/summarize_required_q1_q3.py \
  --baseline-dir "$baseline_dir" \
  --iterative-dir "$iterative_dir" \
  --scoring-metrics outputs/spider_multiseed_experiment/scoring_metrics.json \
  --seeds "${seed_array[@]}" \
  --output "$result_dir/metrics.json"

touch "$result_dir/PIPELINE_COMPLETE"
echo "Completed: $(date)"
echo "Results: $result_dir/metrics.json"
