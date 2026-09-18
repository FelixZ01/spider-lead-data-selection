#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-.venv/bin/python}"
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
export NLTK_DATA="${NLTK_DATA:-$PWD/.cache/nltk}"

processed_dir="data/processed/spider"
experiment_dir="${EXPERIMENT_DIR:-outputs/spider_scaled_experiment}"
source_pool="${SCORED_POOL:-outputs/spider_multiseed_experiment/scored_pool.jsonl}"
budget="${BUDGET:-500}"
epochs="${EPOCHS:-3}"
eval_samples="${EVAL_SAMPLES:-200}"
seed="${SEED:-42}"

mkdir -p "$experiment_dir"

if [[ ! -f "$source_pool" ]]; then
  echo "Missing scored pool: $source_pool" >&2
  echo "Run scripts/run_mac_multiseed_experiment.sh first or set SCORED_POOL." >&2
  exit 1
fi

cp "$source_pool" "$experiment_dir/scored_pool.jsonl"

"$python_bin" src/selection/select_spider.py \
  --input "$experiment_dir/scored_pool.jsonl" \
  --output-dir "$experiment_dir/subsets" \
  --budget "$budget" \
  --seed "$seed"

for method in random uncertainty uncertainty_schema_diverse; do
  echo "=== scaled run: method=$method budget=$budget epochs=$epochs seed=$seed ==="
  run_dir="$experiment_dir/$method"
  "$python_bin" src/training/train_codet5.py \
    --train-file "$experiment_dir/subsets/$method.jsonl" \
    --output-dir "$run_dir/model" \
    --max-samples "$budget" \
    --sample-strategy head \
    --epochs "$epochs" \
    --seed "$seed" \
    --log-every 100
  "$python_bin" src/eval/evaluate_codet5.py \
    --model-dir "$run_dir/model" \
    --eval-file "$processed_dir/dev.jsonl" \
    --output-dir "$run_dir/eval" \
    --max-samples "$eval_samples" \
    --seed 2026
  PREDICTION_JSONL="$run_dir/eval/predictions.jsonl" \
    OFFICIAL_OUTPUT_DIR="$run_dir/official" \
    scripts/run_official_spider_eval.sh "$method" match
done

echo "SCALED_EXPERIMENT_COMPLETED"
