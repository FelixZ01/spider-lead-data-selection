#!/usr/bin/env bash
set -euo pipefail

method="${1:?Usage: scripts/run_official_spider_eval.sh METHOD}"
evaluation_type="${2:-match}"
python_bin="${PYTHON_BIN:-.venv/bin/python}"
export NLTK_DATA="${NLTK_DATA:-$PWD/.cache/nltk}"
experiment_dir="outputs/spider_selection_experiment"
format_dir="$experiment_dir/$method/official"
database_package="${SPIDER_PACKAGE_DIR:-data/raw/spider/databases_package/spider_data}"

"$python_bin" src/eval/export_spider_official.py \
  --input "$experiment_dir/$method/eval/predictions.jsonl" \
  --gold-output "$format_dir/gold.txt" \
  --pred-output "$format_dir/pred.txt"

"$python_bin" external/spider/evaluation.py \
  --gold "$format_dir/gold.txt" \
  --pred "$format_dir/pred.txt" \
  --db "$database_package/database" \
  --table "$database_package/tables.json" \
  --etype "$evaluation_type" > "$format_dir/evaluation.txt"

tail -n 35 "$format_dir/evaluation.txt"
