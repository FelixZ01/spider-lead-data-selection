#!/usr/bin/env bash
set -euo pipefail

python_bin="${PYTHON_BIN:-.venv/bin/python}"
raw_dir="data/raw/spider"
processed_dir="data/processed/spider"
run_dir="outputs/spider_codet5_smoke"
export HF_HOME="${HF_HOME:-$PWD/.cache/huggingface}"

if [[ ! -f "$raw_dir/train_spider.json" ]]; then
  scripts/download_spider.sh "$raw_dir"
fi

"$python_bin" src/data/prepare_spider.py \
  --input "$raw_dir/train_spider.json" \
  --tables-json "$raw_dir/tables.json" \
  --output "$processed_dir/train.jsonl"

"$python_bin" src/data/prepare_spider.py \
  --input "$raw_dir/dev.json" \
  --tables-json "$raw_dir/tables.json" \
  --output "$processed_dir/dev.jsonl"

"$python_bin" src/training/train_codet5.py \
  --train-file "$processed_dir/train.jsonl" \
  --output-dir "$run_dir/model" \
  --max-samples "${TRAIN_SAMPLES:-20}" \
  --epochs "${EPOCHS:-1}"

"$python_bin" src/eval/evaluate_codet5.py \
  --model-dir "$run_dir/model" \
  --eval-file "$processed_dir/dev.jsonl" \
  --output-dir "$run_dir/eval" \
  --max-samples "${EVAL_SAMPLES:-5}"
