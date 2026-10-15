# Historical analysis source snapshots

These are versioned source files used for the article's measurements, separate from the data-free figure renderer. They are preserved at their original paths within three source snapshots. [source-manifest.json](source-manifest.json) pins every source commit/path/hash. Fifteen files were copied without changes on 15 October 2026. In the remaining file, 21_label_partial_credit.py, one docstring sentence quoting a student answer was replaced with a generic duplicate-answer description; executable code is unchanged. The manifest records both original and distributed hashes.

| Snapshot | Entry point | Role |
|---|---|---|
| `teacher-alignment` | [30_jwe_feedback_curves.py](teacher-alignment/experiments/scripts/30_jwe_feedback_curves.py) | Full-grid curves, ICWE reproduction gate, first/sustained target attainment |
| `teacher-alignment` | [31_jwe_n40_agreement.py](teacher-alignment/experiments/scripts/31_jwe_n40_agreement.py) | Agreement, gate/subsets and later P1 recomputation; this is not the missing original P1 analysis script |
| `teacher-alignment` | [13_significance_testing.py](teacher-alignment/experiments/scripts/13_significance_testing.py) | Statistical routine used in the recorded P1 recomputation |
| `teacher-alignment` | [26_rationale_score_consistency.py](teacher-alignment/experiments/scripts/26_rationale_score_consistency.py) | Frozen lexicon and sensitivity instrument |
| `human-reference` | [25_partial_credit_model_vs_human.py](human-reference/experiments/scripts/25_partial_credit_model_vs_human.py) | Partial-credit model/reference comparison and E5 residual-dissent policies |
| `human-reference` | [29_binary_runs_vs_human_reference.py](human-reference/experiments/scripts/29_binary_runs_vs_human_reference.py) | Binary comparisons at all four thresholds |
| `human-reference` | [32_paired_model_vs_label_kappa.py](human-reference/experiments/scripts/32_paired_model_vs_label_kappa.py) | Exploratory paired model-versus-label Δκ with shared text resamples |
| `rationale-judge` | [collect.py](rationale-judge/experiments/judge_20260918/collect.py), [compare_scores.py](rationale-judge/experiments/judge_20260918/compare_scores.py) | Frozen judge contract, collection implementation and later score join |

The remaining files are the original local dependencies, not additional analyses or result sets. No acquisition, annotation, adjudication or metric estimation runs as part of the appendix validation/figure commands.

## Restricted-input reproduction

Full reproduction requires an authorized copy of StudentAssessment-Analysis with the original Git objects, pinned predictions, source pool, human reference and archived agreement records. Those inputs are not distributed here. The code snapshots alone are not a runnable replacement for the restricted analysis repository: some original modules load its analysis plan at import time or read pinned Git blobs.

In an authorized checkout at the commit named for the corresponding snapshot in `source-manifest.json`, the entry-point docstrings give the original commands and input paths. Restore the snapshot files at their recorded repository-relative paths and run there, with that repository's environment and data access. Do not run these entry points inside the public appendix directory. The teacher-alignment sources use their own frozen input Git revisions; preserve those objects rather than substituting current files.

The source snapshots include optional historical CLI functionality as historical source evidence. No individual rating, adjudication record, advisory-note field or advisory-note sensitivity result is distributed or used by this appendix. The [A.7.3 provenance gaps](../07-provenance.md#a73), including lost P1 repeat-control outputs and the missing original P1 script, remain gaps.

## Rendering without restricted inputs

Use [figures/render.py](../figures/render.py) and the included aggregate data to redraw the three diagrams. This does not invoke any source snapshot or perform a bootstrap. The repository [validator](../scripts/validate.py) also requires no restricted inputs.

[Appendix index](../README.md)
