# Spider + CodeT5-small local baseline

This is an observed Apple M3 smoke/small-scale run, not a final research result.

- Training: 200 seeded random Spider examples from 103 databases, one epoch.
- Evaluation: 20 seeded random Spider development examples from nine databases.
- Training time: 37.33 seconds on Apple MPS.
- Loss: 7.7456 initially, 0.8425 on the final step, 1.9106 mean.
- Diagnostic normalized exact match: 1/20 (5%).
- Generation time: 6.55 seconds.

The one exact string match was:

```text
Question: What is the version number and template type code for the template
with version number later than 5?

Gold:       SELECT version_number, template_type_code FROM Templates
            WHERE version_number > 5
Prediction: SELECT Version_Number, Template_Type_Code FROM Templates
            WHERE Version_Number > 5
```

This run proves that download, preprocessing, schema prompting, Apple-MPS
fine-tuning, checkpoint saving, generation, and metric recording work end to end.
The 5% diagnostic score is expected to be weak at this scale. It must not be
reported as official Spider execution accuracy or as evidence that LEAD works.

Next research stage: establish larger full/random baselines, then implement and
compare a documented LEAD-style selection method under the same data budget.
