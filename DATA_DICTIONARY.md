# Data dictionary

[Appendix index](README.md) · [Methods and uncertainty](04-methods.md#a46)

Only aggregate data are supplied. The CSV tables preserve publication formatting; the figure inputs are compact numeric data for plotting. They are not interchangeable row-level datasets.

## Publication tables

[tables/](tables/README.md) contains one Markdown and one UTF-8 CSV file per table. Group headings and multirow column headings remain ordinary CSV rows. Blank cells mean that no value is supplied for that cell; they are not zeros. A dash in the attainment tables means that a target was not reached on the measured grid. `n/a` and `n.a.` mean not applicable; “not measurable” identifies an unavailable arm. Captions define each table's denominator and scope.

Percentages are on a 0–100 scale; kappa and QWK are dimensionless. Parenthesized `k/n` values give agreeing rows over evaluated rows. Brackets in estimate columns denote confidence intervals. Display rounding is retained, so a difference between rounded endpoints can differ from the rounded original difference. Markdown cells may contain emphasis, citations or math notation; the CSV cells contain the corresponding display text without those wrappers.

Table A.14 uses `contradictions/comparable rationales`. The comparable count is the number decided by the instrument with a parseable recorded score, not the total number of inputs. There are 450 inputs per grader and one missing Phi-4 rationale.

## Figure A.1: teacher-label crosstab

File: [teacher_label_crosstab.csv](figures/data/teacher_label_crosstab.csv).

| Field | Meaning |
|---|---|
| `rater` | `jonas` = coder A / JG; `andreas` = coder B / AB |
| `teacher_label` | Historical binary label, 0 = incorrect and 1 = correct |
| `level` | Raw human code, integer 0–4, before adjudication |
| `count` | Number of response records in that cell, after mapping each text's code to its records |

Each rater has ten cells totaling 450 records: 198 historical incorrect labels and 252 correct labels. These are marginal crosstabs for each coder against the teacher label; they cannot reconstruct coder-to-coder agreement or the adjudicated reference.

## Figure A.3: partial-credit agreement

File: [consensus_model_vs_reference.json](figures/data/consensus_model_vs_reference.json).

| Field | Meaning |
|---|---|
| `human_labels.primary_reference` | `soft`: boundary cases contribute half weight per coder's class |
| `human_labels.adjacent_residual_boundary` | 77 distinct texts straddling a three-level class boundary |
| `models` keys | Historical run identifiers for the four partial-credit graders |
| `reference_policies` | `soft`, `strict` (lower boundary class), `lenient` (higher boundary class) |
| `qwk` | Quadratic weighted kappa on the three-level scale, over 450 records |
| `qwk_ci` | Precomputed 95% percentile interval, 10,000 resamples of distinct texts |

The figure shows intervals for `soft` and point estimates for `strict` and `lenient`. Resampling texts keeps all duplicate-text records together. This aggregate file does not contain the resamples or predictions.

## Figure A.4: binary agreement

File: [binary_runs_vs_reference.json](figures/data/binary_runs_vs_reference.json).

| Field | Meaning |
|---|---|
| `primary_threshold` | Raw human level 3, the primary binary threshold |
| `humans.t3.teacher_vs_reference` | Historical label's kappa against the binarized human reference |
| `runs[].model` | Provider or local model identifier |
| `runs[].headline` | Membership in the fifteen binary base arms shown here |
| `runs[].reference_t3.kappa` | Stored binary outcome versus the primary human reference |
| `runs[].reference_t3.kappa_ci` | Precomputed 95% percentile interval, 2,000 resamples of distinct texts |
| `runs[].teacher.kappa` | The same stored binary outcomes versus the historical teacher label |
| `runs[].teacher.kappa_ci` | `null`: no interval supplied in this aggregate export |

All comparisons use 450 stored outcomes, including fallback zeros as documented in [A.6.1](06-human-reference.md#a61). The paired differences in Table A.12 use a separate analysis with 10,000 shared resamples. Their intervals cannot be obtained by subtracting the marginal interval endpoints in this file.

## Integrity and source records

[provenance.json](provenance.json) hashes the distributed files, excluding itself and Git metadata. [reproduction/source-manifest.json](reproduction/source-manifest.json) records the original repository, commit, path and distributed hash for each historical Python source file; the one documented docstring redaction also has its original hash. [figures/provenance.json](figures/provenance.json) records the derivation and original aggregate-input hashes. A matching hash establishes byte identity, not substantive correctness.
