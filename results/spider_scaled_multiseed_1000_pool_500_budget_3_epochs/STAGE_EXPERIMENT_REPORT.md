# Stage Experiment Report

## Lightweight Data Selection for Text-to-SQL

### 1. Objective

This stage investigated whether a lightweight schema-diversity constraint can improve uncertainty-based training-data selection for Text-to-SQL under limited local computing resources. The research goal is not only to increase accuracy, but to determine whether diversity-aware selection can produce better and more stable performance under the same data and computing budget.

### 2. Work completed

Over the past two days, I completed the following pipeline:

1. Prepared Spider examples in a consistent training format.
2. Used the pretrained target loss from CodeT5-small as a static uncertainty score for a candidate pool of 1,000 training examples.
3. Selected 500 examples under the same data budget using three methods:
   - **Random:** uniform random sampling.
   - **Uncertainty:** selecting the examples with the highest pretrained target loss.
   - **Uncertainty + schema diversity:** prioritising high-loss examples while maintaining SQL-complexity proportions and broader database coverage.
4. Fine-tuned `Salesforce/codet5-small` for three epochs on Apple MPS.
5. Repeated training with five seeds: 11, 42, 73, 101, and 202.
6. Evaluated every trained model on the full Spider development set of 1,034 examples using the official Spider exact-match evaluator.
7. Built a resumable unattended pipeline so that the remaining training, evaluation, logging, and result aggregation could continue automatically while I was away for an examination.

### 3. Experimental setup

| Item | Setting |
|---|---|
| Dataset | Spider |
| Candidate pool | 1,000 training examples |
| Selection budget | 500 examples per method |
| Model | Salesforce CodeT5-small |
| Training | 3 epochs, batch size 1, learning rate 5e-5 |
| Device | Apple MPS |
| Seeds | 11, 42, 73, 101, 202 |
| Evaluation set | Full Spider development set, 1,034 examples |
| Main metric | Official Spider exact match |

### 4. Full-development-set results

| Method | Exact match by seed | Mean | Sample SD | Difference from random |
|---|---|---:|---:|---:|
| Random | 13.7, 18.0, 13.7, 15.5, 15.9 | 15.36% | 1.79 pp | 0.00 pp |
| Uncertainty | 12.6, 13.0, 13.1, 15.4, 13.5 | 13.52% | 1.10 pp | -1.84 pp |
| Uncertainty + schema diversity | 17.4, 19.7, 19.1, 16.4, 12.4 | **17.00%** | 2.89 pp | **+1.64 pp** |

The schema-diverse method exceeded random sampling in four of the five seeds and produced the highest observed mean exact match among the tested methods. Its paired improvement over random was +3.7, +1.7, +5.4, +0.9, and -3.5 percentage points across the five seeds. The negative result for seed 202 and the larger standard deviation show that the improvement is promising but not yet stable enough to conclude that it consistently outperforms random sampling.

### 5. Selection behaviour

On the selected training subsets, database coverage was:

| Method | Mean represented databases | Mean exact match |
|---|---:|---:|
| Random | 126.8 | 15.36% |
| Uncertainty | 114 | 13.52% |
| Uncertainty + schema diversity | **137** | **17.00%** |

The three methods show a consistent observed pattern: broader database coverage is associated with higher mean exact match. Pure uncertainty sampling concentrated on fewer databases, while the schema-diversity constraint retained high-loss examples and covered all 137 databases in the candidate pool. This association is a plausible explanation, not yet evidence of causation.

### 6. Interpretation and limitations

- Selecting only the most uncertain examples did not improve performance; difficult examples alone may be redundant or concentrated in a limited set of schemas.
- Combining uncertainty with database and SQL-complexity coverage produced the highest observed mean result under the same 500-example budget.
- Only five training seeds were used, and the schema-diverse result was sensitive to seed 202. The current result should therefore be treated as preliminary evidence, not a statistically conclusive finding.
- The reported metric is official Spider exact match. Execution accuracy is not reported because the legacy Spider database package produced a text-decoding error under the current Python environment.
- The selector is a lightweight static method inspired by LEAD's data-selection motivation. It is not a reproduction of LEAD's online IDU and bandit algorithm.

### 7. Proposed next steps

1. Prioritise a five-way ablation: random; uncertainty; uncertainty plus database diversity; uncertainty plus SQL-complexity balancing; and uncertainty plus both constraints.
2. Analyse seed 202 to distinguish optimisation variance from method-specific failure, including errors by SQL difficulty, invalid SQL, schema-linking errors, and database.
3. Build a selection-budget curve to test whether diversity-aware selection maintains an advantage as the number of selected examples changes.
4. Then add more seeds for stability. A larger model will be considered only after the selection effect is understood under the current controlled setup.

### 8. Current conclusion

Under an equal 500-example training budget, the lightweight uncertainty-plus-schema-diversity method produced the highest observed mean Spider exact match, 17.00%, compared with 15.36% for random selection. Together with its broader database coverage, this is preliminary evidence for a useful diversity effect, not yet a conclusive superiority claim. The next stage will test whether the observed advantage comes from database diversity, SQL-complexity balancing, or their combination.
