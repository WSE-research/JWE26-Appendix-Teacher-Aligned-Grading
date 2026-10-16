# Table A.11: Binary arms against the human reference and teacher label

| Model | Reference $`\geq 3`$ \[95% CI\] | Teacher label | Reference $`\geq 4`$ |
| --- | --- | --- | --- |
| *ICWE models, hosted API (replication arms)* |  |  |  |
| Qwen3.5-397B-A17B | 0.684 \[0.622, 0.745\] | 0.788 | 0.536 |
| Claude Haiku 4.5 | 0.672 \[0.606, 0.733\] | 0.822 | 0.507 |
| DeepSeek V3.2 | 0.649 \[0.581, 0.713\] | 0.793 | 0.463 |
| GLM-4.7 Flash | 0.592 \[0.519, 0.661\] | 0.650 | 0.438 |
| Gemini 2.5 Flash-Lite | 0.577 \[0.507, 0.643\] | 0.686 | 0.570 |
| *Current models of the same price class, hosted API* |  |  |  |
| Gemini 3.5 Flash-Lite$`^{\dagger}`$ | 0.653 \[0.586, 0.714\] | 0.808 | 0.504 |
| GPT-5.6 Luna$`^{\ast}`$ | 0.629 \[0.558, 0.695\] | 0.798 | 0.479 |
| Qwen3.8 Flash$`^{\ddagger}`$ | 0.622 \[0.552, 0.687\] | 0.805 | 0.501 |
| DeepSeek V4 Flash | 0.608 \[0.539, 0.675\] | 0.729 | 0.486 |
| *Open-weight models, served on premises* |  |  |  |
| Qwen3.5-27B | 0.654 \[0.588, 0.715\] | 0.806 | 0.539 |
| Qwen3.6-27B | 0.653 \[0.588, 0.717\] | 0.821 | 0.518 |
| Phi-4 | 0.648 \[0.581, 0.713\] | 0.779 | 0.458 |
| Qwen3-32B | 0.648 \[0.577, 0.716\] | 0.812 | 0.494 |
| Qwen3.8-27B | 0.633 \[0.566, 0.699\] | 0.793 | 0.532 |
| Mistral Small 3.2 | 0.625 \[0.557, 0.690\] | 0.703 | 0.351 |
| Historical teacher label | 0.685 \[0.619, 0.744\] | n/a | 0.479 |

Post hoc exploratory comparison of the fifteen binary base arms with the binarized human reference and with the historical teacher label. Cohen’s kappa over 450 prediction rows (439 texts), one run per model at 40 in-context examples, temperature 0.2 requested. Reference $`\geq 3`$: correct from raw level 3 (primary), with 95% percentile bootstrap interval over texts (2,000 resamples); reference $`\geq 4`$: correct from raw level 4 (sensitivity, point estimate). Residual dissent that straddles a threshold counts half for each side. The last row compares the historical teacher label itself with the reference. Values describe the stored pipeline outcomes. $`^{\ast}`$Temperature setting discarded by the model’s endpoints; run at the model’s default temperature. $`^{\dagger}`$Run with the minimal instead of the disabled reasoning setting, which the model rejects. $`^{\ddagger}`$Includes six failed requests stored with the fallback score 0 and counted as incorrect in both comparisons.

[CSV](table-a11.csv) · [Context](../06-human-reference.md#table-a11)
