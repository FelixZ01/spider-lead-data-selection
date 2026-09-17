#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-.venv/bin/python}"
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
processed_dir="data/processed/spider"
experiment_dir="outputs/spider_selection_experiment"
pool_size="${POOL_SIZE:-1000}"
budget="${BUDGET:-200}"
eval_samples="${EVAL_SAMPLES:-50}"

"$python_bin" src/selection/score_codet5_loss.py \
  --input "$processed_dir/train.jsonl" \
  --output "$experiment_dir/scored_pool.jsonl" \
  --metrics-output "$experiment_dir/scoring_metrics.json" \
  --pool-size "$pool_size"

"$python_bin" src/selection/select_spider.py \
  --input "$experiment_dir/scored_pool.jsonl" \
  --output-dir "$experiment_dir/subsets" \
  --budget "$budget"

for method in random uncertainty uncertainty_schema_diverse; do
  echo "=== Training $method ==="
  "$python_bin" src/training/train_codet5.py \
    --train-file "$experiment_dir/subsets/$method.jsonl" \
    --output-dir "$experiment_dir/$method/model" \
    --max-samples "$budget" \
    --sample-strategy head \
    --epochs 1 \
    --log-every 20
  "$python_bin" src/eval/evaluate_codet5.py \
    --model-dir "$experiment_dir/$method/model" \
    --eval-file "$processed_dir/dev.jsonl" \
    --output-dir "$experiment_dir/$method/eval" \
    --max-samples "$eval_samples"
done
