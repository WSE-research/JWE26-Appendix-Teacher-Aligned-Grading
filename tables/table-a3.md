# Table A.3: Conditions of the 51 arms and decision component

| Condition (role) | Models | Backend | Temp. | $`n`$ | Date |
| --- | --- | --- | --- | --- | --- |
| Original on-prem. base (S1, S2, S4) | Qwen3.6-27B$`^{a}`$, Qwen3.8-27B$`^{a}`$, Phi-4, Mistral Small 3.2 24B | vLLM, local | 0.2 | grid | 17 Aug |
| New on-prem. base (S2, S4, S6) | Qwen3.5-27B$`^{a}`$, Qwen3-32B$`^{a}`$ | vLLM, local | 0.2 | 40 | 16 Sep |
| Replication gate (S3; S2 reference Haiku; S4) | Claude Haiku 4.5, DeepSeek V3.2, Gemini 2.5 Flash-Lite, Qwen3.5-397B-A17B$`^{r}`$, GLM-4.7 Flash$`^{r}`$ | OpenRouter | 0.2 | 40 | 28 Aug |
| Currency tier (expl.) | DeepSeek V4 Flash$`^{r}`$, Qwen3.8 Flash$`^{r}`$, GPT-5.6 Luna$`^{r,t}`$, Gemini 3.5 Flash-Lite$`^{m}`$ | OpenRouter | 0.2 | 0, 5, 20, 40 | 28 Aug |
| P1, local arm (primary) | Mistral Small 3.2 24B | vLLM, local | 0 | grid | 19 Aug |
| P1, API arm (primary) | Mistral Small 3.2 24B | OpenRouter | 0 | grid | 19 Aug |
| P1, first run (superseded, D10) | API arm; local arm = original base run | OpenRouter; vLLM | 0.2 | grid | API: 19 Aug; local: 17 Aug |
| Guided prompt (S1) | four original on-prem. models | vLLM, local | 0.2 | grid | 18 Aug |
| Rationale (RQ4 of the article) | four original on-prem. models | vLLM, local | 0.2 | grid | 18 Aug |
| Partial credit (RQ3 of the article) | four original on-prem. models | vLLM, local | 0.2 | grid | 18 Aug |
| Prompt deconfounding, 3 prompts (expl.) | four original on-prem. models | vLLM, local | 0.2 | grid | 19 Aug |
| Reproducibility reruns (D12) | four original on-prem. models | vLLM, local | 0.2 | grid | 19 Aug |
| Operating-point reruns, one repeat | Qwen3.6-27B$`^{a}`$, Qwen3.8-27B$`^{a}`$ (twice), Phi-4 | vLLM, local | 0 | 40 | 1 Sep |
| Gate repeat | Gemini 2.5 Flash-Lite | OpenRouter | 0.2 | 40 | 28 Aug |
| Decision component (expl.) | Jev 1.13 | OpenRouter Decisions API | default | 0, 5, 20, 40 | 28 Sep |

Grading conditions: the 51 model prediction artifacts of the run selection of 16 September 2026 and the decision component. All generator runs use the fold-wise protocol on the same 450 target rows, an initial output-token budget of 512 (increased on parse retries), JSON requested in the prompt without a response-format constraint, and up to two parse retries. Prompt: base unless the condition names another. Grid: all eleven example counts; single-configuration comparisons use $`n=40`$. $`^{a}`$thinking mode disabled; $`^{r}`$provider reasoning requested disabled; $`^{m}`$minimal reasoning effort requested; $`^{t}`$requested temperature discarded by the provider. The first four rows form the 15 binary base arms (one run per model).

[CSV](table-a3.csv) · [Context](../04-methods.md#table-a3)
