# Table A.4: Uncertainty protocol per analysis

| Analysis | Resampling unit | Interval or test |
| --- | --- | --- |
| P1 (RQ1 of the article) | paired rows (key: question, fold, student, answer text); post hoc: 45 question–fold clusters | 90% bootstrap, 10,000 resamples, seed 42 |
| Agreement per run and $`n`$ (RQ1 of the article, RQ2 of the article) | rows | 95% Wilson interval |
| S1 (RQ1 of the article) | 45 question–fold clusters | cluster-robust p-values (sign-flip permutation, cluster bootstrap); Holm within S1 |
| S2 (RQ1 of the article), planned | 45 question–fold clusters | paired tests against Claude Haiku 4.5; Holm within S2 |
| S6 test (RQ1 of the article), planned | rows | Fisher exact test |
| S6 subsets, descriptive (RQ1 of the article) | rows | 95% Wilson interval |
| Coder agreement (RQ3 of the article) | unique texts; nine questions as clusters | 95% percentile bootstrap, 10,000 resamples, seed 42 |
| Partial credit vs reference (RQ3 of the article) | unique texts | pooled: 95% percentile bootstrap, 10,000 resamples, seed 42; per question: point estimates without intervals |
| Binary runs vs reference (RQ3 of the article), individual $`\kappa`$ | unique texts | 95% percentile bootstrap, 2,000 resamples, seed 42 |
| Paired model–label $`\Delta\kappa`$ (RQ3 of the article), post hoc | unique texts, shared draws for model and label | 95% paired percentile bootstrap, 10,000 resamples, seed 42 |
| Rationale audit (RQ4 of the article) | none (counts) | exact Clopper–Pearson 95% for lexicon counts |
| Decision component (RQ1 of the article) | nine questions as clusters | 95% bootstrap, 10,000 resamples, seed 42 |

Uncertainty quantification per analysis. Bootstraps against the human reference resample unique question–answer texts, so identical texts move together; the P1 bootstrap resamples paired rows, with question–fold clusters as a post hoc sensitivity. Rows marked “planned” describe tests that the analysis plan prescribes but that have not been computed.

[CSV](table-a4.csv) · [Context](../04-methods.md#table-a4)
