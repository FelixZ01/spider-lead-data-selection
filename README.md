# BIRD + LEAD Mini Project

This repository adapts the official [LEAD](https://github.com/HKUSTDial/LEAD) implementation to the BIRD Text-to-SQL dataset for a UQ mini-project.

## Current status

- Official LEAD source is tracked as a Git submodule in `external/LEAD`.
- One real BIRD training example is stored in `data/sample/bird_sample.jsonl`.
- A concise Chinese code guide is available in `notes/LEAD_CODE_GUIDE_CN.md`.
- `src/data/prepare_bird.py` converts BIRD JSON/JSONL plus `tables.json` into Qwen/LEAD chat JSONL.
- GPU training and environment setup will be completed on UQ Bunya after access is approved.

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
