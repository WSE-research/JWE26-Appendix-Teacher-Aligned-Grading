# Table A.1

| Study | Data | Reference labels | Scale | Measures |
| --- | --- | --- | --- | --- |
| Zhao [\[25\]](../references.md#ref-Zhao2025FewShotGraderV1) | 3 public ASAG benchmarks; proofs | Existing instructor grades | 0–100; 7 binary proof items | RMSE, Pearson $`r`$, item accuracy |
| Deng [\[6\]](../references.md#ref-Deng2025RubricConditioned) | SciEntsBank | Inherited benchmark labels | Nominal 2/3/5-way categories | Accuracy, $`\kappa`$, coverage, perturbations |
| Lai [\[12\]](../references.md#ref-Lai2025SASBenchV2) | 4,109 responses | 18 experts: annotation and verification | Overall and step scores; error causes | QWK, CCS, ECS, Micro-F1 |
| Armfield [\[2\]](../references.md#ref-Armfield2025AvalonManuscript) | Pilot, 507 submissions | Calibration, self-grades, dispute review | Rubric items with points | Student–agent agreement, overturns |
| Korthals [\[11\]](../references.md#ref-Korthals2025Canvas) | 6,345 question attempts | Course graders blind to model grades | 0–1 per task, fractional | Agreement, $`r`$, audit, survey |
| Sunkavalli [\[21\]](../references.md#ref-Sunkavalli2026JudgesAsRaters) | 2,377 essays, 12 hosted judges | Pooled scores (PT); two raters (EN) | 0–200 per competency; holistic | Severity, halo, dependability, drift |
| Gur-Arieh [\[8\]](../references.md#ref-GurArieh2026Faithfulness) | Traces of 10 models, 13 tasks | Task-derived labels, sampled checks | Binary faithfulness | Metric AUROC, runtime |
| Rodrı́guez [\[19\]](../references.md#ref-Rodriguez2026LaTA) | One-term course deployment | Instructor rulings on regrade requests | Binary rubric items, summed | Appeal error rate, survey, cohorts |
| Dadu [\[5\]](../references.md#ref-Dadu2025GradeGuard) | Mohler dataset | Mean of two independent evaluators | 0–5 in half points | RMSE, indecisiveness, referral |
| ICWE [\[10\]](../references.md#ref-Gwozdz2026ICWE) | Git course, 450 pairs | Binary teacher ratings (manual review) | Binary | Accuracy, calibration error, coverage, tokens |
| ICALT [\[9\]](../references.md#ref-Gwozdz2026ICALT) | Same course, 1,056 responses | Majority of reconstructed binary labels; 157 dual-rated | Binary | Agreement, $`\kappa`$, coverage and risk |
| This article | Same course, 9 questions, 439 texts, 450 rows | Lecturer-reviewed operational binary labels; two independent model-blind codings, adjudicated for distances of two or more levels | Binary; raw 0–4, mapped to 0/1/2 or binarized | Agreement, $`\kappa`$, QWK, equivalence, consistency, coverage |

Data, reference labels, scales and measures as reported in the inspected version of each source; counts are not comparable across rows. AUROC: area under the receiver operating characteristic curve; PT and EN: Portuguese and English essay corpora; QWK: quadratic weighted kappa; other abbreviations as in the text.

[CSV](table-a1.csv) · [Context](../02-source-comparisons.md#table-a1)
