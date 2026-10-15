# Table A.7

|  | All rows |  | ICWE | Overruled | Confirmed |
| --- | --- | --- | --- | --- | --- |
| Model | % ($`k/n`$) | 95% Wilson | % | $`k/43`$ (%) | % ($`k/n`$) |
| *On premises, original roster (vLLM)* |  |  |  |  |  |
| Qwen3.6-27B | **91.11** (410/450) | \[88.12, 93.40\] |  | 32 (74.42) | 92.87 (378/407) |
| Qwen3.8-27B | 89.56 (403/450) | \[86.39, 92.05\] |  | 33 (76.74) | 90.91 (370/407) |
| Phi-4 | 89.11 (401/450) | \[85.90, 91.66\] |  | 20 (46.51) | 93.61 (381/407) |
| Mistral Small 3.2 24B | 85.78 (386/450) | \[82.25, 88.70\] |  | 13 (30.23) | 91.65 (373/407) |
| *On premises, added in September (vLLM)* |  |  |  |  |  |
| Qwen3-32B | 90.67 (408/450) | \[87.62, 93.02\] |  | 27 (62.79) | 93.61 (381/407) |
| Qwen3.5-27B | 90.22 (406/450) | \[87.13, 92.64\] |  | 34 (79.07) | 91.40 (372/407) |
| *Hosted, ICWE models in the gate run (OpenRouter)* |  |  |  |  |  |
| Claude Haiku 4.5 | **91.11** (410/450) | \[88.12, 93.40\] | 90.67 | 31 (72.09) | 93.12 (379/407) |
| DeepSeek V3.2 | 89.78 (404/450) | \[86.63, 92.25\] | 90.00 | 26 (60.47) | 92.87 (378/407) |
| Qwen3.5-397B-A17B | 89.33 (402/450) | \[86.14, 91.86\] | 89.33 | 31 (72.09) | 91.15 (371/407) |
| Gemini 2.5 Flash-Lite | 84.00 (378/450) | \[80.33, 87.10\] | 86.00 | 32 (74.42) | 85.01 (346/407) |
| GLM-4.7 Flash | 82.67 (372/450) | \[78.90, 85.88\] | 81.78 | 20 (46.51) | 86.49 (352/407) |
| *Hosted, currency tier (OpenRouter)* |  |  |  |  |  |
| Qwen3.8 Flash$`^{\ddagger}`$ | 90.54 (402/444) | \[87.46, 92.93\] |  | 34 (79.07) | 91.77 (368/401) |
| Gemini 3.5 Flash-Lite$`^{\dagger}`$ | 90.44 (407/450) | \[87.38, 92.83\] |  | 30 (69.77) | 92.63 (377/407) |
| GPT-5.6 Luna$`^{\ast}`$ | 90.00 (405/450) | \[86.88, 92.44\] |  | 31 (72.09) | 91.89 (374/407) |
| DeepSeek V4 Flash | 86.44 (389/450) | \[82.97, 89.30\] |  | 27 (62.79) | 88.94 (362/407) |
| GLM-5.3 Flash | not measurable under the study settings |  |  |  |  |
| *Reference lines (S5)* |  |  |  |  |  |
| Majority class | 56.00 (252/450) |  |  | 8 (18.60) | 59.95 (244/407) |
| Incumbent reference | 90.44 (407/450) |  |  | 0 (0.00) | 100.00 (407/407) |
| Constant “incorrect” |  |  |  | 35 (81.40) |  |

Agreement with the teacher label of the 15 binary base arms at 40 in-context examples (one run per model, base prompt, temperature 0.2 requested), on parseable rows, with 95% Wilson intervals; bold: highest. ICWE: agreement in the ICWE run of February 2026, which each gate run must reproduce within $`\pm 3`$ percentage points (S3). Overruled: the 43 rows on which the lecturer overruled the operational grader; confirmed: the 407 rows on which the lecturer confirmed it (S6, descriptive). Reference lines (S5): the majority class always decides “correct”, the incumbent-agreement reference (incumbent reference) reproduces the operational grader, and a constant “incorrect” decision is shown beside the overruled column. $`^{\ast}`$Requested temperature discarded by the model’s endpoints; run at the model’s default temperature. $`^{\dagger}`$Run with the minimal instead of the disabled reasoning setting, which the model rejects. $`^{\ddagger}`$Six failed requests; counting their stored fallback scores of 0 gives 406 of 450 rows (90.22%), treating every failed request as a disagreement with the teacher label gives 402 of 450 (89.33%).

[CSV](table-a7.csv) · [Context](../05-teacher-alignment.md#table-a7)
