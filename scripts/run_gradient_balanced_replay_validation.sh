#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
seed="${SEED:-42}"
output_dir="${OUTPUT_DIR:-outputs/spider_gradient_balanced_replay/seed_$seed}"

export HF_HOME="${HF_HOME:-$project_dir/.cache/huggingface}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export NLTK_DATA="${NLTK_DATA:-$project_dir/.cache/nltk}"

"$python_bin" src/experiments/run_iterative_lead_spider.py \
  --pool-file outputs/spider_multiseed_experiment/scored_pool.jsonl \
  --eval-file data/processed/spider/dev.jsonl \
  --output-dir "$output_dir" \
  --pool-size 1000 --budget 500 --rounds 5 --clusters 2 \
  --training-mode cumulative_union --total-training-steps 1500 \
  --round-step-schedule 100,200,300,400,500 \
  --epochs-per-round 3 --eval-samples 1034 --seed "$seed" \
  --smoothing 0.1 --gamma 0.06 \
  --selection-policy gradient_balanced_replay --max-reuse 1 --device auto

"$python_bin" src/analysis/validate_iterative_run.py --run-dir "$output_dir"
