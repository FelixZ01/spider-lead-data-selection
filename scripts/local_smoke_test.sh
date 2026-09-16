#!/bin/bash
set -euo pipefail

python3 src/data/prepare_bird.py \
  --input data/sample/bird_sample.jsonl \
  --tables-json data/sample/tables_demo.json \
  --output /tmp/bird_sample_qwen.jsonl

python3 src/data/create_baselines.py \
  --input /tmp/bird_sample_qwen.jsonl \
  --output-dir /tmp/bird_baselines \
  --random-size 1 \
  --seed 42

python3 -m unittest discover -s tests -v
python3 -m py_compile \
  src/data/prepare_bird.py \
  src/data/create_baselines.py \
  src/training/train_qwen_lora.py \
  src/eval/generate_sql.py \
  src/metrics/run_and_record.py

echo "Local CPU-only smoke test passed."
