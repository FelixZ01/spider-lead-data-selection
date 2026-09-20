# Spider Text-to-SQL Experiment: Analysis Handoff

## Objective

Evaluate whether a lightweight schema-diversity constraint improves static uncertainty-based training-data selection for a Mac-feasible CodeT5-small Text-to-SQL pipeline.

## Current stage

- Completed full Spider development-set evaluation: 5 training seeds x 3 methods x 1034 examples.
- Training pool: 1,000 examples.
- Equal selection budget: 500 examples per method.
- Training: CodeT5-small for 3 epochs on Apple MPS.
- Primary reported metric: official Spider exact match.

## Results

| Method | Per-seed exact match | Mean | Sample SD | Gain vs random |
|---|---:|---:|---:|---:|
| Random | 13.7%, 18.0%, 13.7%, 15.5%, 15.9% | 15.36% | 1.79 pp | +0.00 pp |
| Uncertainty | 12.6%, 13.0%, 13.1%, 15.4%, 13.5% | 13.52% | 1.10 pp | -1.84 pp |
| Uncertainty + schema diversity | 17.4%, 19.7%, 19.1%, 16.4%, 12.4% | 17.00% | 2.89 pp | +1.64 pp |

## Evidence boundaries

- Official Spider exact match on all 1,034 development examples. Execution accuracy is not reported because the legacy Spider database package triggered a text-decoding failure under modern Python.
- The uncertainty-based selectors are lightweight static methods inspired by LEAD concepts, not a reproduction of LEAD's online IDU and bandit method.
- These experiments use Spider and CodeT5-small, not the planned BIRD + Qwen3 extension.
- With only a small number of seeds, the result should be treated as promising experimental evidence rather than a final claim.

## Please analyse

1. Is the schema-diversity improvement consistent and practically meaningful?
2. What statistical summary is defensible with the available seeds?
3. Which ablation should be run next to isolate the contribution of schema diversity from uncertainty scoring?
4. What are the main threats to validity in the current design?
5. Recommend one compact results table, one figure, and a report structure.
6. Suggest the smallest credible extension toward BIRD + Qwen3 once GPU resources become available.

Do not describe the selector as an official LEAD reproduction and do not reinterpret exact match as execution accuracy.
