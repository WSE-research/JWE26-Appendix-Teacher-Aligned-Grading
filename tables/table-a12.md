# Table A.12: Paired model-versus-label differences

|  | Reference $`\geq 3`$ |  | Reference $`\geq 4`$ |  |
| --- | --- | --- | --- | --- |
| Model | $`\Delta`$ \[95% CI\] | $`p_{\mathrm{Holm}}`$ | $`\Delta`$ \[95% CI\] | $`p_{\mathrm{Holm}}`$ |
| *ICWE models, hosted API (replication arms)* |  |  |  |  |
| Qwen3.5-397B-A17B | $`-0.000`$ \[$`-0.049`$, $`+0.048`$\] | 1.000 | $`+0.057`$ \[$`+0.010`$, $`+0.105`$\] | 0.218 |
| Claude Haiku 4.5 | $`-0.013`$ \[$`-0.060`$, $`+0.033`$\] | 1.000 | $`+0.028`$ \[$`-0.016`$, $`+0.071`$\] | 1.000 |
| DeepSeek V3.2 | $`-0.035`$ \[$`-0.087`$, $`+0.015`$\] | 1.000 | $`-0.016`$ \[$`-0.060`$, $`+0.029`$\] | 1.000 |
| GLM-4.7 Flash | $`-0.093`$ \[$`-0.161`$, $`-0.027`$\] | 0.053 | $`-0.041`$ \[$`-0.103`$, $`+0.020`$\] | 1.000 |
| Gemini 2.5 Flash-Lite | $`-0.107`$ \[$`-0.167`$, $`-0.050`$\] | 0.012 | $`+0.091`$ \[$`+0.034`$, $`+0.147`$\] | 0.022 |
| *Current models of the same price class, hosted API* |  |  |  |  |
| Gemini 3.5 Flash-Lite$`^{\dagger}`$ | $`-0.031`$ \[$`-0.083`$, $`+0.019`$\] | 1.000 | $`+0.025`$ \[$`-0.018`$, $`+0.068`$\] | 1.000 |
| GPT-5.6 Luna$`^{\ast}`$ | $`-0.056`$ \[$`-0.108`$, $`-0.006`$\] | 0.306 | $`+0.000`$ \[$`-0.044`$, $`+0.044`$\] | 1.000 |
| Qwen3.8 Flash$`^{\ddagger}`$ | $`-0.063`$ \[$`-0.112`$, $`-0.014`$\] | 0.132 | $`+0.023`$ \[$`-0.021`$, $`+0.065`$\] | 1.000 |
| DeepSeek V4 Flash | $`-0.077`$ \[$`-0.135`$, $`-0.019`$\] | 0.130 | $`+0.007`$ \[$`-0.046`$, $`+0.059`$\] | 1.000 |
| *Open-weight models, served on premises* |  |  |  |  |
| Qwen3.5-27B | $`-0.031`$ \[$`-0.077`$, $`+0.015`$\] | 1.000 | $`+0.060`$ \[$`+0.019`$, $`+0.104`$\] | 0.078 |
| Qwen3.6-27B | $`-0.031`$ \[$`-0.075`$, $`+0.011`$\] | 1.000 | $`+0.039`$ \[$`-0.001`$, $`+0.080`$\] | 0.600 |
| Phi-4 | $`-0.037`$ \[$`-0.091`$, $`+0.018`$\] | 1.000 | $`-0.021`$ \[$`-0.068`$, $`+0.026`$\] | 1.000 |
| Qwen3-32B | $`-0.037`$ \[$`-0.087`$, $`+0.011`$\] | 1.000 | $`+0.015`$ \[$`-0.026`$, $`+0.057`$\] | 1.000 |
| Qwen3.8-27B | $`-0.052`$ \[$`-0.100`$, $`-0.006`$\] | 0.301 | $`+0.053`$ \[$`+0.010`$, $`+0.098`$\] | 0.218 |
| Mistral Small 3.2 | $`-0.060`$ \[$`-0.123`$, $`+0.002`$\] | 0.533 | $`-0.128`$ \[$`-0.178`$, $`-0.079`$\] | 0.003 |

Post hoc exploratory paired comparison of each binary base arm with the historical teacher label at the binarized human reference. $`\Delta`$: the arm’s Cohen’s kappa against the reference minus the teacher label’s kappa against the same reference (0.685 correct from raw level 3, 0.479 correct from raw level 4), on the same 450 prediction rows (439 texts); one run per model at 40 in-context examples, temperature 0.2 requested. Brackets: 95% paired percentile bootstrap interval over unique texts, with the same 10,000 resamples (seed 42) for the arm and the label. $`p_{\mathrm{Holm}}`$: two-sided bootstrap p-value, Holm-adjusted within the fifteen base arms of a threshold (supplementary). No equivalence margin was set; an interval that includes zero does not show equal agreement. Values describe the stored pipeline outcomes; markers as in Table [A.11](../06-human-reference.md#table-a11). For Qwen3.8 Flash, excluding the six failed requests for arm and label alike gives $`-0.055`$ \[$`-0.104`$, $`-0.007`$\] at level 3 and $`+0.033`$ \[$`-0.007`$, $`+0.073`$\] at level 4.

[CSV](table-a12.csv) · [Context](../06-human-reference.md#table-a12)
