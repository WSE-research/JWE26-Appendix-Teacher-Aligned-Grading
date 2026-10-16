# Table A.9: First and sustained feedback-target attainment

|  | First reaches |  |  | Stays from |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Model | 85% | 88% | 90% | 85% | 90% | $`n=0`$ | $`n=40`$ |
| *ICWE run, 18 February 2026 (OpenRouter, ICWE settings)* |  |  |  |  |  |  |  |
| Claude Haiku 4.5 | 0 | 3 | 10 | 3 | 40 | 87.11 | 90.67 |
| DeepSeek V3.2 | 10 | 15 | 30 | 10 | 40 | 72.89 | 90.00 |
| Qwen3.5-397B-A17B | 5 | 10 | – | 5 | – | 81.11 | 89.33 |
| Gemini 2.5 Flash-Lite | 25 | – | – | 40 | – | 67.56 | 86.00 |
| GLM-4.7 Flash | 10 | – | – | – | – | 80.22 | 81.78 |
| *On premises, original base runs, 17 August 2026 (vLLM)* |  |  |  |  |  |  |  |
| Qwen3.6-27B | 0 | 3 | 5 | 0 | 5 | 85.11 | 91.11 |
| Qwen3.8-27B | 3 | 3 | 10 | 3 | – | 76.22 | 89.56 |
| Phi-4 | 3 | 15 | – | 3 | – | 84.67 | 89.11 |
| Mistral Small 3.2 24B | 0 | – | – | 35 | – | 86.00 | 85.78 |
| *On premises, reproducibility reruns, 19 August 2026 (vLLM)* |  |  |  |  |  |  |  |
| Qwen3.6-27B | 1 | 1 | 5 | 1 | 5 | 84.89 | 90.67 |
| Qwen3.8-27B | 3 | 5 | 10 | 3 | 35 | 77.11 | 90.22 |
| Phi-4 | 3 | 15 | – | 3 | – | 83.78 | 88.89 |
| Mistral Small 3.2 24B | 0 | – | – | – | – | 86.00 | 84.22 |
| *OpenRouter, first P1 API arm, 19 August 2026* |  |  |  |  |  |  |  |
| Mistral Small 3.2 24B | 0 | – | – | – | – | 85.11 | 83.78 |

Threshold attainment for the runs with all eleven example counts, all at temperature 0.2: the smallest number of in-context examples at which agreement with the teacher label first reaches 85%, 88%, and 90% (the rule of the ICWE paper’s Table 3), and the smallest number from which it stays at or above 85% and 90% at every larger count; “–” means not reached. The last two columns give agreement (%) without examples and with 40. The ICWE rows are recomputed from the archived ICWE predictions and equal the published values. Reference lines (S5) at every count: majority class 56.00%, incumbent-agreement reference 90.44%.

[CSV](table-a9.csv) · [Context](../05-teacher-alignment.md#table-a9)
