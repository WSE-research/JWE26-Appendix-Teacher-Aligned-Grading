# Table A.2

| Study | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Zhao et al. [\[25\]](../references.md#ref-Zhao2025FewShotGraderV1) | Y | U | U | P | N | N | U | N |
| Deng et al. [\[6\]](../references.md#ref-Deng2025RubricConditioned) | Y | U | U | P | P | N | P | Y |
| Lai et al. [\[12\]](../references.md#ref-Lai2025SASBenchV2) | Y | P | Y | Y | Y | N | U | N |
| Armfield et al. [\[2\]](../references.md#ref-Armfield2025AvalonManuscript) | P | U | P | P | U | U | U | N |
| Korthals et al. [\[11\]](../references.md#ref-Korthals2025Canvas) | Y | U | U | Y | P | N | U | N |
| Sunkavalli [\[21\]](../references.md#ref-Sunkavalli2026JudgesAsRaters) | Y | P | U | Y | N | P | Y | N |
| Rodrı́guez [\[19\]](../references.md#ref-Rodriguez2026LaTA) | N | N | P | P | P | N | U | N |
| Dadu et al. [\[5\]](../references.md#ref-Dadu2025GradeGuard) | Y | Y | P | Y | N | N | Y | P |
| ICWE [\[10\]](../references.md#ref-Gwozdz2026ICWE) | P | N | N | N | N | N | N | Y |
| ICALT [\[9\]](../references.md#ref-Gwozdz2026ICALT) | P | P | P | N | N | N | U | Y |
| This article | P | Y | Y | Y | P | Y | P | Y |

Attributes relevant to this article. Y (yes): the inspected version reports the attribute; N (no): the inspected version reports a design that excludes it; P (partial): reported for part of the data or in a weaker form, explained in the text; U (unknown): not reported in the inspected version, which does not mean it was absent. A1: reference produced independently of the evaluated model’s output; A2: independent double human rating documented; A3: adjudication or disagreement resolution documented; A4: partial-credit or ordinal human scale; A5: rationale or explanation evaluated; A6: deployment or serving comparison of the same declared model; A7: repeated-call stability reported; A8: selective deferral reported with coverage. For this article, A1 is P because the operational teacher label is anchored to the deployed grader while the independent reference is model-blind, and A3 refers to the adjudication of disagreements of two or more levels, with adjacent disagreements retained as residual dissent. Gur-Arieh et al. [\[8\]](../references.md#ref-GurArieh2026Faithfulness) are omitted because they do not grade student work. The table records scope differences and supports no conclusion about grading quality.

[CSV](table-a2.csv) · [Context](../02-source-comparisons.md#table-a2)
