#!/usr/bin/env bash
set -euo pipefail

base_dir="${EXPERIMENT_DIR:-outputs/spider_multiseed_experiment}"
seeds="${SEEDS:-11 42 73}"

for seed in $seeds; do
  for method in random uncertainty uncertainty_schema_diverse; do
    run_dir="$base_dir/seed_$seed/$method"
    echo "=== official Spider match: seed=$seed method=$method ==="
    PREDICTION_JSONL="$run_dir/eval/predictions.jsonl" \
      OFFICIAL_OUTPUT_DIR="$run_dir/official" \
      scripts/run_official_spider_eval.sh "$method" match
  done
done

echo "MULTISEED_OFFICIAL_EVAL_COMPLETED"
