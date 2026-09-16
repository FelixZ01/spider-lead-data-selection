#!/bin/bash
#SBATCH --job-name=bird-qwen-smoke
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

# Bunya account/partition/module directives are deliberately omitted until RCC
# confirms the allocation. Submit from the repository root after setting:
#   export VENV_PATH=/absolute/path/to/your/venv

: "${VENV_PATH:?Set VENV_PATH to the Bunya virtual environment}"
source "${VENV_PATH}/bin/activate"
mkdir -p logs outputs/smoke

python src/metrics/run_and_record.py \
  --name qwen3-smoke \
  --output outputs/smoke/runtime.json \
  -- python src/training/train_qwen_lora.py \
    --train-file data/sample/bird_sample_qwen.jsonl \
    --output-dir outputs/smoke/model \
    --model Qwen/Qwen3-1.7B \
    --max-samples 1 \
    --epochs 1 \
    --max-length 512
