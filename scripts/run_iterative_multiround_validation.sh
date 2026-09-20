#!/usr/bin/env bash
set -Eeuo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

python_bin="${PYTHON_BIN:-.venv/bin/python}"
seed="${SEED:-42}"
output_dir="${OUTPUT_DIR:-outputs/spider_iterative_multiround_cumulative/seed_$seed}"
lock_dir=".cache/iterative_multiround_validation.lock"
pid_file=".cache/iterative_multiround_validation.pid"

export HF_HOME="${HF_HOME:-$project_dir/.cache/huggingface}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export NLTK_DATA="${NLTK_DATA:-$project_dir/.cache/nltk}"

mkdir -p .cache logs "$(dirname "$output_dir")"
if ! mkdir "$lock_dir" 2>/dev/null; then
  echo "Another multi-round validation appears to be active: $lock_dir" >&2
  exit 1
fi
echo "$$" > "$pid_file"

caffeinate_pid=""
cleanup() {
  if [[ -n "$caffeinate_pid" ]]; then
    kill "$caffeinate_pid" 2>/dev/null || true
  fi
  rm -f "$pid_file"
  rmdir "$lock_dir" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu -w "$$" &
  caffeinate_pid="$!"
fi

echo "Started five-round validation: $(date)"
echo "Seed: $seed"
"$python_bin" src/experiments/run_iterative_lead_spider.py \
  --pool-file outputs/spider_multiseed_experiment/scored_pool.jsonl \
  --eval-file data/processed/spider/dev.jsonl \
  --output-dir "$output_dir" \
  --pool-size 1000 --budget 500 --rounds 5 --clusters 2 \
  --training-mode cumulative_union --total-training-steps 1500 \
  --epochs-per-round 3 --eval-samples 1034 --seed "$seed" \
  --smoothing 0.1 --gamma 0.06

"$python_bin" src/analysis/validate_iterative_run.py --run-dir "$output_dir"
echo "Completed five-round validation: $(date)"
echo "Results: $output_dir"
