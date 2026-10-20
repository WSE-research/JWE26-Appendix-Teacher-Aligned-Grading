# Reviewer guide

[Appendix index](README.md)

This appendix provides the methods, aggregate results and source snapshots behind *Teacher-Aligned Grading in Web-Based Assessment*. The following distinctions are useful before reading the comparisons.

## References and scales

| Term | Meaning | Used for |
|---|---|---|
| Historical teacher label | Binary operational grader decision, confirmed or inverted during lecturer review | Examples in prompts; teacher-alignment comparisons in RQ1 and RQ2 |
| Independent human reference | Two model-blind author codings, with joint adjudication of disagreements of at least two raw levels and adjacent disagreements retained | Partial-credit and binary comparisons in RQ3 |
| Recorded score | The decision returned with a rationale in the same model output | Internal score-rationale consistency in RQ4, not factual correctness |

The human reference is model-blind, but the authors had prior exposure to the course materials. It is not an external population of raters. [A.4.3](04-methods.md#a43) describes blinding and adjudication in full.

| Scale | Values or rule | Interpretation |
|---|---|---|
| Raw human rating | 0 to 4 | Five semantic levels retained in the coding records |
| Partial-credit analysis | 0 → 0; 1, 2, 3 → 1; 4 → 2 | No credit, partial credit, full credit; compared with model `level` |
| Primary binary reference | Raw level ≥ 3 | Correct core without incorrect statements |
| Stricter binary sensitivity | Raw level ≥ 4 | Fully correct |

At a class boundary, an unresolved adjacent disagreement contributes half weight to each coder's class. It is not rounded into a new agreed label. Strict, lenient and exclusion variants are sensitivity analyses.

## Units and denominators

- **450 response records:** nine questions with 50 records each. Each record yields a separate grading call at a given example count.
- **439 distinct question–answer texts:** each coder rated each text once. Ratings are mapped back to all matching response records. Neither count is the number of students.
- **45 question–fold clusters:** five folds per question. At 40 examples, the ten test records in a cluster share their example set.
- **15 binary base arms versus 51 model prediction artifacts:** the main binary comparison uses one base arm per model; the larger selection also includes prompt variants and controls. The exploratory Jev decision component is separate.

The held-out unit is a response record, not necessarily a distinct answer text. An identical text from another student may appear among the examples; [A.4.2](04-methods.md#a42) gives the overlap counts and [A.5.2.5](05-teacher-alignment.md#a525) describes the overlap-free Jev sensitivity.

Teacher-alignment percentages use parseable outputs. The binary human-reference analysis uses stored pipeline outcomes, including fallback zeros in three arms. In particular, Qwen3.8 Flash has 444 parseable decisions for teacher alignment but 450 stored outcomes for the human-reference comparison. [A.5.1](05-teacher-alignment.md#a51) and [A.6.1](06-human-reference.md#a61) identify the affected cases.

## A focused route through the evidence

| Review question | Start with | Interpretation boundary |
|---|---|---|
| Are serving configurations equivalent? | [A.5.2.4](05-teacher-alignment.md#a524) | The planned temperature-0.2 comparison did not establish equivalence. The temperature-0 follow-up met the margin after an outcome-informed amendment; identical hosted weights are unverified. |
| Does adding examples consistently help? | [Tables A.9 and A.10](05-teacher-alignment.md#a53) | First attainment and sustained attainment differ. Four-point trajectories cannot establish attainment on the full eleven-point grid. |
| Do the models agree with the new human reference? | [Figure A.3](06-human-reference.md#figure-a3), [binary comparison](06-human-reference.md#a613) | Partial-credit QWK and binary Cohen's kappa are different measures. Threshold and residual-dissent policy matter. |
| Is a model better than the historical label against that reference? | [Table A.12](06-human-reference.md#table-a12) | Paired differences use shared resamples. Overlapping marginal intervals, or a difference interval containing zero, do not establish equivalence. |
| Are rationales consistent with their scores? | [Table A.14](06-human-reference.md#table-a14) and [A.6.2](06-human-reference.md#a62) | Contradictions need their comparable-case denominator. Instruments cover different subsets; none was validated against human rationale judgments. |
| Which claims are exploratory or incomplete? | [Analysis protocol](04-methods.md#a46), [provenance](07-provenance.md#a73) | S2/S6 were computed late; S2 depends on the test convention and S6 is not error detection. S4 remains uncomputed because confidence has no defined event. |

## What can be checked from this repository?

| Operation | Public inputs sufficient? | Entry point |
|---|---|---|
| Check hashes, local links, table copies and source pins | Yes | `python3 scripts/validate.py` |
| Recalculate selected aggregate relationships | Yes | `python3 scripts/check_aggregates.py` |
| Redraw the three diagrams using the supplied estimates and intervals | Yes, with plotting dependencies | [Rendering instructions](figures/README.md) |
| Recompute model metrics, paired tests and bootstrap intervals | No; requires restricted inputs and historical Git objects | [Analysis snapshots](reproduction/README.md) |
| Recompute historical API repeat-control discordances | No; prediction CSVs have not been recovered | [Historical evidence summary](reproduction/p1-repeat-controls.md) |

The aggregate checker verifies internal consistency, not the underlying student-level data or the statistical validity of the study. All checks are offline; none submits model requests. The study remains limited to this repeatedly examined course pool.
