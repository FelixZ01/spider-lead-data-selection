# Dynamic Gradient LEAD Adaptation: Multi-seed Analysis

## Controlled question

Under a fixed 500-example and 1,500-step budget, does the dynamic gradient-based LEAD adaptation provide stable gains for Spider Text-to-SQL, and which components explain its behaviour?

All selected-data methods use CodeT5-small, a 1,000-example candidate pool, a 500-example unique-data budget, 1,500 optimizer steps, the full 1,034-example Spider development set, and seeds 11, 42, 73, 101, and 202.

## Main results

| Method | Exact match, mean ± SD |
|---|---:|
| Dynamic gradient + EXP3 + replay | 15.94% ± 2.32% |
| Balanced-cluster replay control | 15.02% ± 3.05% |
| Random (500 examples) | 15.64% ± 1.13% |
| Observed-loss IDU | 17.08% ± 2.39% |
| Full Data (1,000 examples) | 23.02% ± 1.83% |

## Paired findings

- Versus balanced-cluster replay: mean difference +0.92 percentage points; 95% paired interval [-3.30, +5.14]; wins/ties/losses = 3/0/2.
- Versus Random: mean difference +0.30 percentage points; 95% paired interval [-3.02, +3.62]; wins/ties/losses = 3/0/2.
- Versus observed-loss IDU: mean difference -1.14 percentage points; 95% paired interval [-6.27, +3.99]; wins/ties/losses = 1/0/4.
- Versus the previous five-round adaptation: mean difference +0.72 percentage points; 95% paired interval [-3.59, +5.03]; wins/ties/losses = 3/0/2.
- Versus Full Data: mean difference -7.08 percentage points; 95% paired interval [-9.89, -4.27]; wins/ties/losses = 0/0/5.

None of the paired intervals against the selected-data baselines excludes zero. The dynamic method should therefore be described as competitive, not consistently superior.

## Selection and timing behaviour

- Dynamic selections have mean pairwise Jaccard overlap 0.80; the fixed balanced control has overlap 1.00.
- The dynamic method covers 123.2 databases on average; the balanced control covers 122.0.
- Mean end-to-end time is 489.2 seconds for dynamic EXP3 and 430.9 seconds for the balanced control.
- EXP3 changes the selected difficulty path, but its five decisions are insufficient to establish a stable policy across seeds.

## Critical interpretation

Cumulative replay is the clearest successful design change: it raises the dynamic seed-42 run from 10.3% without replay to 19.5% with replay. Across five seeds, however, the dynamic method averages 15.94%, only 0.30 percentage points above Random and 0.92 points above the matched balanced control. The result varies substantially with seed, so the large seed-42 gain is an example of why multi-seed validation is necessary.

The current evidence does not show that EXP3 or the gradient proxy reliably improves final accuracy. It does show a complete dynamic selection loop, exposes the effect of forgetting, and provides a controlled negative or mixed result that can be analysed rather than hidden.

## Limitations and next step

The main limitations are the five-seed sample, task-specific loss-quantile clusters, a final-decoder-block gradient proxy instead of LoRA-gradient geometry, only five bandit decisions, and exact-match-only evaluation. The next justified experiment is not another broad parameter sweep. It is a targeted reward-design test or a higher-frequency allocation design, motivated by the observation that current rewards mostly rise with training round and weakly distinguish difficulty arms.
