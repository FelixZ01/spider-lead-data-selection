#!/bin/bash
# Run the official BIRD execution-accuracy evaluator after downloading its repo.
set -euo pipefail

: "${BIRD_REPO:?Set BIRD_REPO to the cloned AlibabaResearch/DAMO-ConvAI/bird directory}"
: "${BIRD_DB_ROOT:?Set BIRD_DB_ROOT to dev_databases/ (include trailing slash)}"
: "${BIRD_DEV_JSON:?Set BIRD_DEV_JSON to dev.json}"
: "${BIRD_GOLD_DIR:?Set BIRD_GOLD_DIR to the directory containing dev_gold.sql (include trailing slash)}"
: "${PREDICTION_DIR:?Set PREDICTION_DIR to the directory containing predict_dev.json (include trailing slash)}"

python "${BIRD_REPO}/llm/src/evaluation.py" \
  --db_root_path "${BIRD_DB_ROOT}" \
  --predicted_sql_path "${PREDICTION_DIR}" \
  --data_mode dev \
  --ground_truth_path "${BIRD_GOLD_DIR}" \
  --num_cpus "${NUM_CPUS:-8}" \
  --mode_gt gt \
  --mode_predict gpt \
  --diff_json_path "${BIRD_DEV_JSON}" \
  --meta_time_out "${SQL_TIMEOUT:-30}"
