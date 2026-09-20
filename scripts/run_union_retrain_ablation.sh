#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
seeds="${SEEDS:-11 42 73 101 202}"
source_dir="outputs/spider_required_q1_q3_iterative"
output_dir="outputs/spider_iterative_union_retrain"
result_dir="results/spider_iterative_union_retrain"
eval_file="data/processed/spider/dev.jsonl"

export HF_HOME="${HF_HOME:-$project_dir/.cache/huggingface}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export NLTK_DATA="${NLTK_DATA:-$project_dir/.cache/nltk}"

mkdir -p "$output_dir" "$result_dir" logs

echo "Started union-retrain ablation: $(date)"
echo "Seeds: $seeds"

for seed in $seeds; do
  echo "=== Fresh union retrain: seed=$seed ==="
  "$python_bin" src/experiments/run_iterative_union_retrain.py \
    --selection-dir "$source_dir/seed_$seed" \
    --eval-file "$eval_file" \
    --output-dir "$output_dir/seed_$seed" \
    --budget 500 --epochs 3 --seed "$seed"
done

read -r -a seed_array <<< "$seeds"
"$python_bin" src/analysis/summarize_union_retrain_ablation.py \
  --required-metrics results/spider_required_q1_q3/metrics.json \
  --ablation-dir "$output_dir" \
  --seeds "${seed_array[@]}" \
  --output "$result_dir/metrics.json"

touch "$result_dir/PIPELINE_COMPLETE"
echo "Completed union-retrain ablation: $(date)"
echo "Results: $result_dir/metrics.json"
