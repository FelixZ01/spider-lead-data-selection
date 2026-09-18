#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-.venv/bin/python}"
export NLTK_DATA="${NLTK_DATA:-$PWD/.cache/nltk}"

seed="${SEED:-42}"
base_dir="${EXPERIMENT_DIR:-outputs/spider_scaled_multiseed_experiment}"
seed_dir="$base_dir/seed_$seed"
eval_file="data/processed/spider/dev.jsonl"

for method in random uncertainty uncertainty_schema_diverse; do
  run_dir="$seed_dir/$method"
  eval_dir="$run_dir/full_dev_eval"
  official_dir="$run_dir/full_dev_official"
  if [[ -f "$official_dir/evaluation.txt" ]]; then
    echo "=== already complete: seed=$seed method=$method full dev ==="
    continue
  fi
  echo "=== full development evaluation: seed=$seed method=$method ==="
  "$python_bin" src/eval/evaluate_codet5.py \
    --model-dir "$run_dir/model" \
    --eval-file "$eval_file" \
    --output-dir "$eval_dir" \
    --max-samples 999999 \
    --sample-strategy head \
    --seed 2026 \
    --quiet
  PREDICTION_JSONL="$eval_dir/predictions.jsonl" \
    OFFICIAL_OUTPUT_DIR="$official_dir" \
    scripts/run_official_spider_eval.sh "$method" match
done

echo "FULL_DEV_EVALUATION_COMPLETED"
