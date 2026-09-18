# Final experiment analysis task

The unattended local experiment has completed. Read these files:

- `results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs/CHATGPT_ANALYSIS_BRIEF.md`
- `results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs/full_dev_multiseed_metrics.json`
- `results/spider_scaled_multiseed_1000_pool_500_budget_3_epochs/metrics.json`
- the relevant source files under `src/selection/`, `src/training/`, and `src/eval/`

Produce a rigorous but readable final analysis in English. Include:

1. An executive summary with the main numerical result.
2. A per-method comparison across all completed seeds.
3. Consistency, variance, effect size, and what can or cannot be inferred from the sample size.
4. A clear explanation of why schema diversity may help Text-to-SQL data selection.
5. Threats to validity and possible confounders.
6. The most informative next ablation and the smallest credible BIRD + Qwen3 extension.
7. A concise paragraph suitable for a progress email to the supervisors.

Respect the evidence boundaries in the handoff. Do not call this an official LEAD reproduction. Do not describe exact match as execution accuracy. Do not modify project files; return only the analysis.
