# Late-computed secondary tests S2 and S6

Source: StudentAssessment-Analysis commit `d1cfc59c4c99b7890a7b46c884ca45a5c43d36b7`, computed 20 October 2026. Outputs are aggregate-only; no student responses or row-level records are included. Exact source paths and hashes are in [the source manifest](../source-manifest.json).

S2 and S6 were computed on 20 October 2026 from stored predictions, after descriptive values had been reported on 13 October. The S2 reference run, the only Claude Haiku 4.5 run under the harmonized settings, was named on that date. Extending the S1 cluster sign-flip convention to S2 was also recorded then (D21), after the descriptive values were known; both the cluster and exact McNemar tests are therefore reported. Declared family sizes were retained. S4 remains uncomputed because the prompt requests a confidence value without defining its event.

- [S2 paired counts, agreement, intervals and both p-value conventions](s2_onprem_vs_claude_haiku.csv): six model comparisons, 450 paired rows each, 45 prompt clusters, Holm family size six. Agreement and cluster interval endpoints are proportions; the difference column is percentage points. No equivalence margin was declared.
- [S6 subset counts, agreement and Fisher tests](s6_new_models_fisher.csv): two models, 43 overruled and 407 confirmed rows, Holm family size two. Agreement and Wilson bounds are proportions. The constant-incorrect reference is 35/43; the split is not an error-detection test.
- [Computation metadata](meta.json) and [independent aggregate check](independent_check/verify_out.json), including the within-cluster S6 sensitivity. These are unmodified historical outputs; statements about what was fixed before data existed must be read with the explicit late reference-run designation and test-convention qualification above.
- [Analysis source snapshot](../teacher-alignment/experiments/scripts/33_jwe_s2_s6_tests.py), using the sibling `31_jwe_n40_agreement.py` and `jwe_pinned_inputs.py`. Full reproduction requires the restricted Git objects and scientific Python dependencies described in [the reproduction guide](../README.md).

These files synchronize the appendix with results already reported in article 8caf0b9; this editorial update did not run new grading or inferential analyses.
