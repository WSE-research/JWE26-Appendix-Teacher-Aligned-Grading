# Table A.5

| Comparison | Collection | Valid and missing cases |
| --- | --- | --- |
| Agreement of the base arms (RQ1 of the article) | 15 arms $`\times`$ 450 rows | 14 arms 450 parseable; Qwen3.8 Flash 444 (6 failed requests); GLM-5.3 Flash not measurable |
| Further conditions and controls (RQ1 of the article) | 36 artifacts $`\times`$ 450 rows | 3 unparseable outputs (2 Qwen3.8-27B, deconfounding prompt; 1 Phi-4, rationale prompt) |
| Serving substitution P1 (RQ1 of the article) | 2 runs $`\times`$ 2 arms $`\times`$ 450 rows | all 1,800 outputs parseable; 450 pairs per run |
| Decision component (RQ1 of the article) | 4 example counts $`\times`$ 450 calls | 1,800 usable; 3 flagged probability sums |
| Feedback curves, full grid (RQ2 of the article) | 11 runs $`\times`$ 11 counts $`\times`$ 450 rows; ICWE: 5 models $`\times`$ 11 $`\times`$ 450 | all cells 450 parseable |
| Feedback, currency tier (RQ2 of the article) | 4 models $`\times`$ 4 counts $`\times`$ 450 rows | Qwen3.8 Flash 445, 444, 447, 444 parseable; others 450 |
| Partial credit, models (RQ3 of the article) | 4 runs $`\times`$ 450 rows | all 1,800 outputs parseable |
| Partial credit, humans (RQ3 of the article) | 2 coders $`\times`$ 439 unique texts | 439 of 439 per coder; 71 distances $`\geq 2`$ adjudicated; 152 distance-1 cases residual dissent |
| Rationale audit (RQ4 of the article) | 4 runs $`\times`$ 450 rationales | 1 missing (Phi-4); 1,799 judgments per judge |
| September 2026 OpenRouter acquisition | not used | 1,807 valid, 1,341 unattempted, 2 failed attempts; incomplete |

Data available per comparison. Rows are target rows of the 450-row pool at 40 in-context examples unless stated otherwise; missing or unusable cases remain visible as separate states and are never replaced by values.

[CSV](table-a5.csv) · [Context](../05-teacher-alignment.md#table-a5)
