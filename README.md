# BIRD + LEAD Mini Project

This repository contains two staged routes for a UQ Text-to-SQL mini-project:

1. A Mac-feasible Spider 1.0 + CodeT5-small baseline.
2. A later BIRD + Qwen3 + LEAD extension when suitable GPU compute is available.

## Current status

- Official LEAD source is tracked as a Git submodule in `external/LEAD`.
- One real BIRD training example is stored in `data/sample/bird_sample.jsonl`.
- A concise Chinese code guide is available in `notes/LEAD_CODE_GUIDE_CN.md`.
- `src/data/prepare_bird.py` converts BIRD JSON/JSONL plus `tables.json` into Qwen/LEAD chat JSONL.
- A local Spider + CodeT5-small smoke pipeline is available for Apple Silicon.
- The BIRD/Qwen path remains prepared for later GPU access.
- A verified 200-example Apple-MPS run is recorded in
  `results/spider_codet5_200/` (37.33 seconds training; 1/20 diagnostic match).

## Run the local Mac baseline

Create a Python 3.12 environment and install the small local stack:

```bash
/Users/Zhuanz/miniforge3/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-mac.txt
scripts/run_mac_spider_smoke.sh
```

The script downloads the official Spider `train_spider.json`, `dev.json`, and
`tables.json`, prepares schema-aware CodeT5 inputs, fine-tunes on 20 examples,
and generates five development predictions. Raw data, processed data, and model
checkpoints are ignored by Git.

The local exact-match number is only a pipeline diagnostic. It is not presented
as official Spider execution accuracy.

## Run the CPU-only preprocessing demo

```bash
python3 src/data/prepare_bird.py \
  --input data/sample/bird_sample.jsonl \
  --tables-json data/sample/tables_demo.json \
  --output data/sample/bird_sample_qwen.jsonl

python3 -m unittest discover -s tests -v
```

`tables_demo.json` is only a minimal test fixture. Replace it with the official BIRD `tables.json` when the full dataset is available.

## Planned experiment

Compare the same Qwen3 model under three training-data strategies:

1. Full BIRD training data.
2. A random subset of the same size as LEAD's selected subset.
3. A LEAD-selected subset.

Primary quality metric: execution accuracy (EX). Efficiency metrics: selected sample count, selection time, training time, peak GPU memory, and total end-to-end time.

## Prepared experiment tools

- `src/data/create_baselines.py`: creates deterministic Full and Random baselines.
- `src/training/train_qwen_lora.py`: Qwen3-1.7B LoRA training entry point for Bunya.
- `src/metrics/run_and_record.py`: records wall time, exit status, and observed GPU memory.
- `src/eval/generate_sql.py`: deterministic Qwen generation in official BIRD prediction format.
- `scripts/run_official_bird_ex.sh`: wrapper around BIRD's official EX evaluator.
- `scripts/bunya_smoke.slurm`: one-example, one-epoch Bunya smoke-test template.
- `scripts/local_smoke_test.sh`: CPU-only validation that is safe to run locally.

The final EX score is produced with the official BIRD evaluation package. A custom SQL-result comparison is intentionally not presented as official EX.

Official evaluator source: `AlibabaResearch/DAMO-ConvAI/bird/llm/src/evaluation.py`.

## Important boundary

The official LEAD code targets general instruction-tuning datasets. It cannot be run on BIRD unchanged. BIRD formatting, schema injection, Text-to-SQL evaluation, and Bunya job scripts still need to be added and verified.
