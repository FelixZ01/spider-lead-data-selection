#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
seeds="${SEEDS:-11 42 73 101 202}"
experiment_dir="${EXPERIMENT_DIR:-outputs/spider_iterative_lead_1000_pool_500_budget_2_rounds}"
result_dir="${RESULT_DIR:-results/spider_iterative_lead_1000_pool_500_budget_2_rounds}"
lock_dir=".cache/iterative_lead_pipeline.lock"
pid_file=".cache/iterative_lead_pipeline.pid"

export HF_HOME="${HF_HOME:-$project_dir/.cache/huggingface}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export NLTK_DATA="${NLTK_DATA:-$project_dir/.cache/nltk}"

mkdir -p .cache logs "$experiment_dir" "$result_dir"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another iterative pipeline appears to be active: $lock_dir" >&2
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

echo "=== Stage 1/4: unit tests ==="
"$python_bin" -m unittest discover -s tests -v

echo "=== Stage 2/4: small end-to-end smoke test ==="
smoke_dir="outputs/iterative_lead_smoke_v2_seed42"
"$python_bin" src/experiments/run_iterative_lead_spider.py \
  --pool-file outputs/spider_multiseed_experiment/scored_pool.jsonl \
  --eval-file data/processed/spider/dev.jsonl \
  --output-dir "$smoke_dir" \
  --pool-size 120 --budget 40 --rounds 2 --clusters 2 \
  --epochs-per-round 1 --eval-samples 50 --seed 42 \
  --smoothing 0.1 --gamma 0.06

if [[ ! -f "$smoke_dir/final_official/evaluation.txt" ]]; then
  PREDICTION_JSONL="$smoke_dir/final_eval/predictions.jsonl" \
    OFFICIAL_OUTPUT_DIR="$smoke_dir/final_official" \
    bash scripts/run_official_spider_eval.sh simplified_iterative_lead match
fi

echo "=== Stage 3/4: five formal seeds ==="
for seed in $seeds; do
  seed_dir="$experiment_dir/seed_$seed"
  echo "--- formal seed=$seed ---"
  "$python_bin" src/experiments/run_iterative_lead_spider.py \
    --pool-file outputs/spider_multiseed_experiment/scored_pool.jsonl \
    --eval-file data/processed/spider/dev.jsonl \
    --output-dir "$seed_dir" \
    --pool-size 1000 --budget 500 --rounds 2 --clusters 2 \
    --epochs-per-round 3 --eval-samples 1034 --seed "$seed" \
    --smoothing 0.1 --gamma 0.06

  if [[ ! -f "$seed_dir/final_official/evaluation.txt" ]]; then
    PREDICTION_JSONL="$seed_dir/final_eval/predictions.jsonl" \
      OFFICIAL_OUTPUT_DIR="$seed_dir/final_official" \
      bash scripts/run_official_spider_eval.sh simplified_iterative_lead match
  fi
done

echo "=== Stage 4/4: aggregate and compare ==="
read -r -a seed_array <<< "$seeds"
"$python_bin" src/analysis/summarize_iterative_lead.py \
  --experiment-dir "$experiment_dir" \
  --baseline-metrics results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs/full_dev_multiseed_metrics.json \
  --seeds "${seed_array[@]}" \
  --output "$result_dir/metrics.json"

touch "$result_dir/PIPELINE_COMPLETE"
echo "Completed: $(date)"
echo "Final metrics: $result_dir/metrics.json"
