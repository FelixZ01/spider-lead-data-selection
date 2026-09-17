#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-.venv/bin/python}"
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"
export NLTK_DATA="${NLTK_DATA:-$PWD/.cache/nltk}"
processed_dir="data/processed/spider"
base_dir="outputs/spider_multiseed_experiment"
pool_size="${POOL_SIZE:-1000}"
budget="${BUDGET:-200}"
eval_samples="${EVAL_SAMPLES:-100}"
pool_seed="${POOL_SEED:-42}"
seeds="${SEEDS:-11 42 73}"

mkdir -p "$base_dir"

if [[ ! -f "$base_dir/scored_pool.jsonl" ]]; then
  "$python_bin" src/selection/score_codet5_loss.py \
    --input "$processed_dir/train.jsonl" \
    --output "$base_dir/scored_pool.jsonl" \
    --metrics-output "$base_dir/scoring_metrics.json" \
    --pool-size "$pool_size" \
    --seed "$pool_seed"
fi

for seed in $seeds; do
  seed_dir="$base_dir/seed_$seed"
  "$python_bin" src/selection/select_spider.py \
    --input "$base_dir/scored_pool.jsonl" \
    --output-dir "$seed_dir/subsets" \
    --budget "$budget" \
    --seed "$seed"

  for method in random uncertainty uncertainty_schema_diverse; do
    echo "=== seed=$seed method=$method ==="
    run_dir="$seed_dir/$method"
    "$python_bin" src/training/train_codet5.py \
      --train-file "$seed_dir/subsets/$method.jsonl" \
      --output-dir "$run_dir/model" \
      --max-samples "$budget" \
      --sample-strategy head \
      --epochs 1 \
      --seed "$seed" \
      --log-every 50
    "$python_bin" src/eval/evaluate_codet5.py \
      --model-dir "$run_dir/model" \
      --eval-file "$processed_dir/dev.jsonl" \
      --output-dir "$run_dir/eval" \
      --max-samples "$eval_samples" \
      --seed 2026
  done
done

echo "MULTISEED_EXPERIMENT_COMPLETED"
