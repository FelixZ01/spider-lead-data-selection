# LEAD-to-Spider Implementation Alignment

This note separates the paper's method from the adaptations used in the
Spider + CodeT5-small study. The purpose is to make every experimental claim
traceable and to avoid treating an approximation as a faithful reproduction.

| LEAD component | Paper implementation | Current Spider implementation | Status |
| --- | --- | --- | --- |
| Initial utility | Target-token training loss | CodeT5 target-token loss | Closely aligned |
| Dynamic utility | IDU with historical smoothing and gradient-based loss-change approximation | Observed-loss-change IDU obtained by rescoring the remaining pool | Adapted, but not inference-free |
| Training-time gradient IDU | Utility change estimated from gradients and parameter updates during ordinary training | First-order gradient/update inner product on the final CodeT5 decoder block, with historical smoothing | New controlled adaptation |
| Difficulty clustering | IFD followed by K-means | Quantiles of pretrained target loss | Simplified |
| Task clustering | Instruction embeddings followed by K-means | Spider database IDs or global selection | Simplified |
| Cluster scheduler | EXP3 using IDU reduction as reward | EXP3 with bounded observed utility-reduction reward | Simplified |
| Online selection | Repeated model-aware selection with bounded reuse | Five rounds under a fixed event and optimizer-step budget | Aligned in workflow |
| Efficiency objective | Avoid repeated candidate-pool inference | Observed-loss IDU rescored the remaining pool; the new gradient variant updates utility during training | The new variant targets the paper's efficiency idea |

## Controlled research question

Under the same model, candidate pool, selection-event budget, optimizer-step
budget, evaluation set, and seeds, does training-time gradient IDU provide a
better performance-cost trade-off than Random, static uncertainty, and the
observed-loss-change IDU adaptation?

## Hypothesis

Training-time gradient IDU will reduce selection overhead because it does not
rescore the remaining candidate pool after each round. It may also provide a
more stable model-aware utility signal than static uncertainty. However, its
performance may be limited because CodeT5-small is fully fine-tuned and the
gradient estimate tracks only the final decoder block rather than LoRA
parameters used by the original implementation.

## Competing explanations

1. Any improvement may come from repeated exposure to difficult examples,
   rather than from the gradient utility itself.
2. A final-decoder-block gradient may not represent the effect of the full
   parameter update.
3. The 1,000-example pool and five selection rounds may be too small for the
   utility signal to stabilize.
4. Text-to-SQL structure may require schema- or SQL-aware grouping before MAB
   allocation becomes useful.

## Scope boundary

The training-time gradient variant is closer to LEAD's inference-free idea,
but it is still an adaptation. It does not yet reproduce IFD clustering,
semantic task clustering, the exact coefficient derivation, or the LoRA-based
parameter-change estimator from the official implementation.
