# Three-seed Spider selection experiment

This experiment tests whether the preliminary one-seed result remains stable
across training seeds 11, 42, and 73.

## Shared setup

- Hardware: Apple M3 MacBook Air, 16 GB unified memory
- Model: `Salesforce/codet5-small`
- Device: Apple MPS
- Candidate pool: 1,000 Spider 1.0 training examples
- Selection budget: 200 examples per method
- Training: one epoch
- Evaluation: the same fixed 100-example development subset (19 databases,
  evaluation seed 2026)
- Quality metric: official Spider exact match

## Per-seed results

| Training seed | Method | Selected DBs | Train time (s) | Official exact match |
|---:|---|---:|---:|---:|
| 11 | Random | 95 | 26.11 | 5/100 (5%) |
| 11 | Uncertainty | 78 | 23.24 | 1/100 (1%) |
| 11 | Uncertainty + schema diversity | 120 | 23.82 | 0/100 (0%) |
| 42 | Random | 94 | 24.36 | 2/100 (2%) |
| 42 | Uncertainty | 78 | 25.91 | 1/100 (1%) |
| 42 | Uncertainty + schema diversity | 120 | 26.10 | 4/100 (4%) |
| 73 | Random | 96 | 27.08 | 1/100 (1%) |
| 73 | Uncertainty | 78 | 25.40 | 2/100 (2%) |
| 73 | Uncertainty + schema diversity | 120 | 26.30 | 2/100 (2%) |

## Aggregate results

Values are mean +/- sample standard deviation over the three training seeds.

| Method | Selected DBs | Train time (s) | Official exact match |
|---|---:|---:|---:|
| Random | 95.0 +/- 1.0 | 25.85 +/- 1.38 | 2.67% +/- 2.08% |
| Uncertainty | 78.0 +/- 0.0 | 24.85 +/- 1.41 | 1.33% +/- 0.58% |
| Uncertainty + schema diversity | 120.0 +/- 0.0 | 25.41 +/- 1.38 | 2.00% +/- 2.00% |

## Interpretation

The one-seed apparent accuracy gain did not hold consistently across three
training seeds. Random selection has the highest mean exact match here, but its
variance is also high; with only 100 evaluation examples and very low absolute
scores, this experiment does not establish an accuracy winner.

The robust finding is coverage: adding the lightweight schema-diversity
constraint selected examples from 120 databases, compared with 78 for pure
uncertainty and about 95 for random selection, without materially increasing
training time. This supports schema diversity as a useful selection-property
control, but not yet as evidence of higher Text-to-SQL accuracy.

The next defensible experiment is to increase the training budget and/or
training epochs before moving to a stronger model. The evaluation subset should
also be enlarged once the pipeline is stable.

## Reproduce the report

After completing the nine training runs:

```bash
bash scripts/run_official_spider_multiseed_eval.sh
.venv/bin/python src/analysis/summarize_multiseed.py \
  --experiment-dir outputs/spider_multiseed_experiment \
  --output results/spider_multiseed_1000_pool_200_budget/metrics.json
```

## Boundaries

- The uncertainty methods are static pretrained-loss baselines inspired by
  LEAD concepts. They are not an official reproduction of LEAD's IDU or online
  bandit algorithm.
- Execution accuracy is not reported because the legacy Spider database
  package triggered a text-decoding failure on one SQLite row under modern
  Python.
- Checkpoints, raw data, and prediction files remain local and are ignored by
  Git. This directory contains the compact, reproducible result summary.
