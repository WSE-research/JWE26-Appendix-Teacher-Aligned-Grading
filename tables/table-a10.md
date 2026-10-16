# Table A.10: Agreement over the full example-count grid

| Run | 0 | 1 | 3 | 5 | 10 | 15 | 20 | 25 | 30 | 35 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Haiku 4.5, ICWE | 87.11 | 82.67 | 88.22 | 88.67 | 90.44 | 87.78 | 90.89 | 90.67 | 90.67 | 89.78 | 90.67 |
| DeepSeek V3.2, ICWE | 72.89 | 74.22 | 81.56 | 84.67 | 87.33 | 88.89 | 88.67 | 88.89 | 90.00 | 89.78 | 90.00 |
| Qwen3.5-397B, ICWE | 81.11 | 83.78 | 84.89 | 87.33 | 88.00 | 86.22 | 87.33 | 86.44 | 87.78 | 88.89 | 89.33 |
| Gemini 2.5 FL, ICWE | 67.56 | 75.56 | 81.56 | 82.67 | 84.22 | 84.67 | 84.67 | 86.67 | 85.33 | 84.22 | 86.00 |
| GLM-4.7 Flash, ICWE | 80.22 | 81.33 | 82.67 | 79.78 | 85.11 | 85.33 | 82.67 | 81.33 | 83.56 | 82.22 | 81.78 |
| Qwen3.6-27B, on-prem. | 85.11 | 87.56 | 88.44 | 91.11 | 92.00 | 90.89 | 91.78 | 91.56 | 91.78 | 90.89 | 91.11 |
| Qwen3.8-27B, on-prem. | 76.22 | 84.00 | 88.89 | 88.89 | 90.00 | 90.44 | 89.78 | 90.22 | 88.89 | 90.22 | 89.56 |
| Phi-4, on-prem. | 84.67 | 83.56 | 86.44 | 85.33 | 86.00 | 88.67 | 87.56 | 87.33 | 87.11 | 86.67 | 89.11 |
| Mistral 3.2, on-prem. | 86.00 | 82.67 | 79.11 | 83.56 | 82.00 | 83.56 | 85.56 | 85.33 | 84.89 | 85.11 | 85.78 |
| Qwen3.6-27B, rerun | 84.89 | 88.00 | 88.44 | 91.56 | 92.44 | 91.33 | 91.56 | 91.56 | 92.00 | 91.11 | 90.67 |
| Qwen3.8-27B, rerun | 77.11 | 84.00 | 87.11 | 88.00 | 90.22 | 91.33 | 91.11 | 90.22 | 89.56 | 90.00 | 90.22 |
| Phi-4, rerun | 83.78 | 82.89 | 86.00 | 85.33 | 86.22 | 88.22 | 88.00 | 88.00 | 87.56 | 87.33 | 88.89 |
| Mistral 3.2, rerun | 86.00 | 80.89 | 79.78 | 81.56 | 82.00 | 84.44 | 86.22 | 86.44 | 84.44 | 84.44 | 84.22 |
| Mistral 3.2, API | 85.11 | 81.56 | 79.33 | 82.00 | 80.89 | 83.11 | 84.22 | 85.11 | 83.78 | 83.56 | 83.78 |

Agreement with the teacher label (%) by number of in-context examples $`n`$ for the runs of Table [A.9](../05-teacher-alignment.md#table-a9), all at temperature 0.2, each cell on 450 parseable rows. ICWE: run of 18 February 2026 through OpenRouter under the ICWE settings (Haiku 4.5: Claude Haiku 4.5; Gemini 2.5 FL: Gemini 2.5 Flash-Lite); on-prem.: original base runs of 17 August 2026; rerun: reproducibility reruns of 19 August 2026; API: first P1 API arm. Reference lines (S5) at every $`n`$: majority class 56.00%, incumbent-agreement reference 90.44%.

[CSV](table-a10.csv) · [Context](../05-teacher-alignment.md#table-a10)
