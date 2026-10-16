# Table A.6: ICWE replication gate

| Model | ICWE run | Gate run | Diff. (pp) | Within $`\pm 3`$ |
| --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | 90.67 | 91.11 | $`+0.44`$ | yes |
| DeepSeek V3.2 | 90.00 | 89.78 | $`-0.22`$ | yes |
| Qwen3.5-397B-A17B | 89.33 | 89.33 | $`0.00`$ | yes |
| Gemini 2.5 Flash-Lite | 86.00 | 84.00 | $`-2.00`$ | yes |
| GLM-4.7 Flash | 81.78 | 82.67 | $`+0.89`$ | yes |
| Gemini 2.5 Flash-Lite, repeat | 86.00 | 83.56 | $`-2.44`$ | (control) |

Replication gate S3: agreement with the teacher label (%) of the five hosted ICWE models at 40 examples on the same 450 rows, in the ICWE run of February 2026 (initial output-token budget 250, response-format constraint) and in the gate run of 28 August 2026 (initial budget 512, no constraint; parse retries could increase both budgets); both through OpenRouter at temperature 0.2. The criterion is a difference within $`\pm 3`$ percentage points. The last row is a repeat of the Gemini 2.5 Flash-Lite gate run, reported as a control.

[CSV](table-a6.csv) · [Context](../05-teacher-alignment.md#table-a6)
