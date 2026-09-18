#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-.venv/bin/python}"
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
export NLTK_DATA="${NLTK_DATA:-$PWD/.cache/nltk}"

processed_dir="data/processed/spider"
base_dir="${EXPERIMENT_DIR:-outputs/spider_scaled_multiseed_experiment}"
source_pool="${SCORED_POOL:-outputs/spider_multiseed_experiment/scored_pool.jsonl}"
budget="${BUDGET:-500}"
epochs="${EPOCHS:-3}"
eval_samples="${EVAL_SAMPLES:-200}"
seeds="${SEEDS:-11 42 73}"

if [[ ! -f "$source_pool" ]]; then
  echo "Missing scored pool: $source_pool" >&2
  exit 1
fi

mkdir -p "$base_dir"

for seed in $seeds; do
  seed_dir="$base_dir/seed_$seed"
  mkdir -p "$seed_dir"
  if [[ ! -f "$seed_dir/subsets/selection_summary.json" ]]; then
    "$python_bin" src/selection/select_spider.py \
      --input "$source_pool" \
      --output-dir "$seed_dir/subsets" \
      --budget "$budget" \
      --seed "$seed"
  fi

  for method in random uncertainty uncertainty_schema_diverse; do
    run_dir="$seed_dir/$method"
    if [[ -f "$run_dir/official/evaluation.txt" ]]; then
      echo "=== already complete: seed=$seed method=$method ==="
      continue
    fi
    echo "=== scaled run: seed=$seed method=$method budget=$budget epochs=$epochs ==="
    "$python_bin" src/training/train_codet5.py \
      --train-file "$seed_dir/subsets/$method.jsonl" \
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
done

echo "SCALED_MULTISEED_EXPERIMENT_COMPLETED"
