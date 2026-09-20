#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
output_dir="${OUTPUT_DIR:-outputs/spider_iterative_multiround_smoke}"

export HF_HOME="${HF_HOME:-$project_dir/.cache/huggingface}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export NLTK_DATA="${NLTK_DATA:-$project_dir/.cache/nltk}"

echo "=== Stage 1/3: unit tests ==="
"$python_bin" -m unittest discover -s tests -v

echo "=== Stage 2/3: five-round cumulative smoke run ==="
"$python_bin" src/experiments/run_iterative_lead_spider.py \
  --pool-file outputs/spider_multiseed_experiment/scored_pool.jsonl \
  --eval-file data/processed/spider/dev.jsonl \
  --output-dir "$output_dir" \
  --pool-size 120 --budget 40 --rounds 5 --clusters 2 \
  --training-mode cumulative_union --total-training-steps 40 \
  --epochs-per-round 1 --eval-samples 20 --seed 42 \
  --smoothing 0.1 --gamma 0.06

echo "=== Stage 3/3: invariant validation ==="
"$python_bin" src/analysis/validate_iterative_run.py --run-dir "$output_dir"

echo "MULTIROUND_SMOKE_COMPLETE"
