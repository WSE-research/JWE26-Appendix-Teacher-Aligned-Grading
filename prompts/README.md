# Exact prompt templates and output contracts

These files contain instructions and empty runtime slots only. They contain no student responses. The grading templates request JSON through their wording; they are not server-enforced JSON schemas. The rationale judges use an enforced schema.

| Condition | File |
|---|---|
| Binary base | [base.txt](base.txt) |
| Rationale | [rationale.txt](rationale.txt) |
| Partial credit | [partial_credit.txt](partial_credit.txt) |
| Guided, S1 | [guided.txt](guided.txt) |
| ICALT base, deconfounding reference | [icalt_base.txt](icalt_base.txt) |
| ICALT base plus completeness | [guided_rubric_only.txt](guided_rubric_only.txt) |
| ICALT base with guided confidence | [guided_conf_only.txt](guided_conf_only.txt) |
| Shared score-blind rationale judge | [judge.txt](judge.txt) |
| Enforced judge output schema | [judge-schema.json](judge-schema.json) |

The rationale judge's user message is a JSON object with the single field `reason`, whose value is the rationale being read. The grade, confidence, source model, question, separate student-answer field and human labels are absent.

## Grading user message template

```text
Question:
{question_text}

Human-rated examples for this same question:
Example {i} answer:
{example_i_answer_text}
Example {i} human_rating: {0|1}

Target student answer:
{target_answer}
```

Repeat the example block for each sampled example. At zero examples use `No human-rated examples provided (baseline round).` in place of the entire example block. Runtime question/answer slots are German course content, while the prompt templates are English. The examples keep binary labels even for the partial-credit condition.

Source: grading configuration files at StudentAssessment-Analysis `225061256f988e54fcec8fa9d2d6cb8647b796d8`; shared judge prompt/schema at `3dcd7fbab3d1b69a4f79fa4b87d783cd2f8f64c0`. See [A.4.5](../04-methods.md#a45) for conditions and [A.4.4](../04-methods.md#a44) for judge settings.

[Appendix index](../README.md)
