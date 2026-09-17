# Equal-budget Spider selection experiment

This observed Mac experiment compares three 200-example subsets selected from
the same seeded 1,000-example Spider pool. Every model starts from the same
CodeT5-small checkpoint, trains for one epoch, and is evaluated on the same 50
seeded development examples.

| Method | Databases covered | Mean selection loss | Train time | Official Spider exact match |
| --- | ---: | ---: | ---: | ---: |
| Random | 94 | 7.4267 | 28.30 s | 1/50 (2%) |
| Uncertainty | 78 | 9.6703 | 25.98 s | 2/50 (4%) |
| Uncertainty + schema diversity | 120 | 9.0145 | 26.78 s | 2/50 (4%) |

The exact-match scores were confirmed with the official Spider evaluator. The
preliminary result is consistent with the idea that high-loss examples can
be more useful than a random subset at a very small budget. The diversity
constraint preserved the same diagnostic score while expanding database
coverage from 78 to 120. This is a promising hypothesis, not a conclusion:
the evaluation set is small and only one seed was used. Execution accuracy is
not reported because one legacy Spider SQLite row caused a text-decoding error
under the current Python runtime.

## Method boundary

These are static, compute-aware selection baselines inspired by LEAD. They are
not an official LEAD reproduction. Official LEAD uses iterative instance-level
dynamic uncertainty, loss-change approximations, historical smoothing,
clustering, and an online multi-armed bandit. The current Mac method uses a
single pretrained target loss and a deterministic database/complexity coverage
constraint. The distinction must remain explicit in reports and emails.
