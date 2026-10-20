# Table A.14: Score-rationale contradictions and comparable-case denominators

| Grader | Lexicon rule | Sensitivity variant | Gemma judge | Qwen judge |
| --- | --- | --- | --- | --- |
| Mistral Small 3.2 | 0/370 | 39/421 | 3/434 | 2/405 |
| Phi-4 | 2/339 | 40/407 | 24/441 | 4/393 |
| Qwen3.6-27B | 0/343 | 14/387 | 0/450 | 0/447 |
| Qwen3.8-27B | 4/320 | 18/365 | 0/450 | 0/449 |

Exploratory score-rationale audit: contradictions / comparable rationales, where comparable means decided by the instrument with a parseable recorded score. There are 450 input rows per grader (one Phi-4 row without a rationale), 40 in-context examples and temperature 0.2. No human reference is involved. Instrument coverage differs, so these columns do not establish a ranking. Values reproduce the accompanying article’s score-rationale table (`tab:c2`, Table 7 in the accompanying revision).

[CSV](table-a14.csv) · [Context](../06-human-reference.md#table-a14)
