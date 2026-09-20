# BIRD + LEAD Mini Project

This repository contains two staged routes for a UQ Text-to-SQL mini-project:

1. A Mac-feasible Spider 1.0 + CodeT5-small baseline.
2. A later BIRD + Qwen3 + LEAD extension when suitable GPU compute is available.

## Current status

### Five-round compute-matched iterative validation

The current LEAD-style validation uses five selection rounds with a fixed total
budget of 500 examples.  Each round adds 100 examples to a cumulative training
set, while the optimizer-step budget is fixed at 1,500 steps in total (300 per
round).  This keeps the training-step budget aligned with the 500-example,
three-epoch random baseline while giving EXP3 multiple opportunities to update.

Run the small end-to-end check first:

```bash
bash scripts/run_iterative_multiround_smoke.sh
```

Then run one formal seed before expanding to all seeds:

```bash
bash scripts/run_iterative_multiround_validation.sh
```

Check its progress with:

```bash
bash scripts/status_iterative_multiround_validation.sh
```

- Official LEAD source is tracked as a Git submodule in `external/LEAD`.
- One real BIRD training example is stored in `data/sample/bird_sample.jsonl`.
- A concise Chinese code guide is available in `notes/LEAD_CODE_GUIDE_CN.md`.
- `src/data/prepare_bird.py` converts BIRD JSON/JSONL plus `tables.json` into Qwen/LEAD chat JSONL.
- A local Spider + CodeT5-small smoke pipeline is available for Apple Silicon.
- The BIRD/Qwen path remains prepared for later GPU access.
- A verified 200-example Apple-MPS run is recorded in
  `results/spider_codet5_200/` (37.33 seconds training; 1/20 diagnostic match).
- An equal-budget 1,000-pool/200-selected experiment is recorded in
  `results/spider_selection_1000_pool_200_budget/`. Static uncertainty and
  uncertainty-plus-schema-diversity both reached 2/50 official Spider exact
  matches versus 1/50 for random selection; this is preliminary and not
  official LEAD.
- A three-seed robustness experiment is recorded in
  `results/spider_multiseed_1000_pool_200_budget/`. The earlier accuracy gain
  did not reproduce consistently: random, uncertainty, and
  uncertainty-plus-schema-diversity averaged 2.67%, 1.33%, and 2.00% official
  exact match, respectively. The reliable result was broader database coverage
  from the schema-diversity constraint (120 databases versus 78 for pure
  uncertainty and 95 for random selection).
- A scaled three-seed experiment is recorded in
  `results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs/`. With 500
  selected examples and three epochs, uncertainty plus schema diversity reached
  15.33% +/- 1.53% official exact match, compared with 12.00% +/- 1.80% for
  random and 11.00% +/- 1.73% for pure uncertainty. It ranked first for all
  three training seeds while covering all 137 candidate-pool databases. On the
  complete 1,034-example Spider development set, schema-diverse uncertainty
  averaged 18.73% official exact match across three seeds, compared with 15.13%
  for random and 12.90% for pure uncertainty selection.

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

## Run the equal-budget selection experiment

```bash
POOL_SIZE=1000 BUDGET=200 EVAL_SAMPLES=50 \
  scripts/run_mac_selection_experiment.sh
```

This compares random selection, pretrained-loss uncertainty selection, and a
schema-diverse uncertainty variant. These lightweight methods are explicitly
LEAD-inspired static baselines, not a reproduction of LEAD's online IDU and
bandit algorithm.

With the official Spider databases available locally, run official exact-match
and execution evaluation for one method with:

```bash
scripts/run_official_spider_eval.sh uncertainty_schema_diverse match
```

The official evaluator is tracked as the `external/spider` Git submodule.
`match` is the default because some original Spider SQLite rows contain legacy
text encodings that can make execution evaluation fail under modern Python.

For an unattended three-seed robustness run:

```bash
POOL_SIZE=1000 BUDGET=200 EVAL_SAMPLES=100 SEEDS="11 42 73" \
  scripts/run_mac_multiseed_experiment.sh
```

Then run official Spider exact match and build the compact result file:

```bash
bash scripts/run_official_spider_multiseed_eval.sh
.venv/bin/python src/analysis/summarize_multiseed.py \
  --experiment-dir outputs/spider_multiseed_experiment \
  --output results/spider_multiseed_1000_pool_200_budget/metrics.json
```

For the scaled three-seed experiment:

```bash
SEEDS="11 42 73" BUDGET=500 EPOCHS=3 EVAL_SAMPLES=200 \
  bash scripts/run_mac_scaled_multiseed_experiment.sh

.venv/bin/python src/analysis/summarize_multiseed.py \
  --experiment-dir outputs/spider_scaled_multiseed_experiment \
  --output results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs/metrics.json
```

## Run unattended on a Mac

The unattended runner resumes completed work instead of repeating it. By
default it keeps seeds 11, 42, and 73, adds seeds 101 and 202, runs full
development-set evaluation, builds aggregate JSON files, and creates a concise
experiment analysis brief. Waiting, model execution, and summary generation use
local Python:

```bash
bash scripts/start_unattended_mac_pipeline.sh
```

This launches the pipeline in the background so closing the terminal does not
stop it. Monitor it from another terminal with:

```bash
bash scripts/monitor_unattended_pipeline.sh
```

The runner uses `caffeinate` to prevent ordinary macOS sleep while it is active.
Keep the Mac connected to power and leave the lid open. Logs are written under
`logs/`; completed checkpoints and evaluation files are detected automatically.
The monitor estimates the finish time from measured training and generation
times in completed runs.

## Final Spider study results

The controlled study compares Full Data, Random, static uncertainty, two-round
iterative selection, five-round IDU-only selection, and the clustering,
bandit, and database-allocation ablations. All selected-data methods use the
same 500-example budget; the five-round variants share the same cumulative
training schedule and optimizer-step budget.

The strongest selected-data method is five-round IDU-only, with 17.08% mean
official Spider exact match across five seeds, compared with 15.64% for Random
and 23.02% for Full Data. This is a promising but seed-sensitive result rather
than a statistically conclusive superiority claim.

Key artifacts:

- `Spider_LEAD_Final_Experiment_Report.pdf`
- `results/spider_final_analysis/REPORT.md`
- `results/spider_final_analysis/analysis.json`
- `results/spider_required_q1_q3/metrics.json`
- `results/spider_iterative_idu_only/metrics.json`

## Run the simplified iterative LEAD-style experiment

The iterative route keeps the 1,000-example pool and 500-example total budget,
but selects two batches of 250 examples. It uses two target-loss difficulty
clusters, an EXP3 scheduler, observed loss changes as a transparent IDU proxy,
and Spider database IDs as task groups. This tests the LEAD workflow locally;
it is not the paper's inference-free gradient-based implementation.

```bash
bash scripts/start_iterative_lead_pipeline.sh
bash scripts/monitor_iterative_lead_pipeline.sh
```

To leave a five-minute local watchdog running without starting final analysis:

```bash
bash scripts/monitor_iterative_lead_pipeline.sh --watch
```

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
