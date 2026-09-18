# Scaled three-seed Spider selection experiment

This experiment follows the initial 200-example study by increasing both the
selection budget and training duration. Its purpose is to test whether schema
diversity remains useful once the CodeT5-small baseline has enough data to move
beyond near-zero exact match.

## Shared setup

- Hardware: Apple M3 MacBook Air, 16 GB unified memory
- Model: `Salesforce/codet5-small`
- Device: Apple MPS
- Candidate pool: 1,000 Spider 1.0 training examples
- Selection budget: 500 examples per method
- Training: 3 epochs, batch size 1
- Training seeds: 11, 42, and 73
- Evaluation: the same fixed 200-example development subset (19 databases,
  evaluation seed 2026)
- Primary metric: official Spider exact match

## Per-seed results

| Seed | Random | Uncertainty | Uncertainty + schema diversity |
|---:|---:|---:|---:|
| 11 | 11.5% | 13.0% | **14.0%** |
| 42 | 14.0% | 10.0% | **17.0%** |
| 73 | 10.5% | 10.0% | **15.0%** |

The schema-diverse method achieved the highest official exact match under all
three training seeds.

## Aggregate results

Values are mean +/- sample standard deviation over the three training seeds.

| Method | Selected DBs | Train time (s) | Official exact match |
|---|---:|---:|---:|
| Random | 126.0 +/- 1.7 | 241.90 +/- 64.90 | 12.00% +/- 1.80% |
| Uncertainty | 114.0 +/- 0.0 | 257.34 +/- 46.67 | 11.00% +/- 1.73% |
| Uncertainty + schema diversity | **137.0 +/- 0.0** | 267.73 +/- 78.80 | **15.33% +/- 1.53%** |

Relative to random selection, the schema-diverse method improved mean exact
match by 3.33 percentage points while covering all 137 databases in the
candidate pool. Pure uncertainty selection concentrated on fewer databases and
did not outperform random selection on average.

## Interpretation

Increasing the budget from 200 to 500 examples and training from one to three
epochs raised official exact match into the 10--17% range. This confirms that
the earlier 0--5% results were strongly limited by under-training.

The repeated advantage of schema-diverse uncertainty selection is encouraging:
it balances high-loss examples with broader database coverage, avoiding the
concentration produced by pure uncertainty selection. However, this is still a
small local experiment on one fixed 200-example evaluation subset. It supports
the method as a promising hypothesis, not as a final statistically established
result.

## Recommended next step

Before increasing model size, perform error analysis on the three seed-42
models and evaluate the selected approach on a larger or full Spider development
set. This distinguishes data-selection effects from errors caused by schema
linking, invalid SQL, joins, or unsupported query complexity.

## Reproduce

```bash
SEEDS="11 42 73" BUDGET=500 EPOCHS=3 EVAL_SAMPLES=200 \
  bash scripts/run_mac_scaled_multiseed_experiment.sh

.venv/bin/python src/analysis/summarize_multiseed.py \
  --experiment-dir outputs/spider_scaled_multiseed_experiment \
  --output results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs/metrics.json
```

## Boundaries

- These are static pretrained-loss baselines inspired by LEAD concepts, not an
  official reproduction of LEAD's IDU or online bandit algorithm.
- Execution accuracy is not reported because one legacy Spider SQLite row
  causes a text-decoding failure under modern Python.
- Checkpoints, raw data, official-evaluator logs, and predictions remain local
  and are ignored by Git.
