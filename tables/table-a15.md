# Table A.15: Detailed evaluation design

| RQ | Change examined | Reference | Comparison construct and unit | Status |
| --- | --- | --- | --- | --- |
| RQ1 | Extended model set and prompt variants: ICWE models (rerun), open-weight and current hosted models | Teacher label | Agreement; parseable outputs per arm | S3 replication criterion; S1 (replication), S2, S4, S6 secondary; S5 descriptive; rest exploratory |
| RQ1 | Serving path for the same declared open-weight model: vLLM inference server versus hosted API (hosted weight identity unverified) | Teacher label | Paired difference in agreement, read against repeat discordance | P1, primary (equivalence) |
| RQ1 | Decision component (Jev) behind the adapter; offline referral | Teacher label | Agreement; coverage and agreement of accepted decisions | Exploratory |
| RQ2 | Number of teacher-rated examples for the new models | Teacher label | Agreement per example count; threshold attainment | Exploratory |
| RQ3 | Output scale: partial-credit level | Independent model-blind reference; teacher label for contrast | Partial-credit agreement (QWK); rows, inter-rater agreement over distinct texts | Exploratory |
| RQ3 | Binary decisions of the base arms | Human reference binarized from its five-level scale (A.4.3); teacher label for contrast | Binary agreement with the reference (Cohen's $\kappa$); rows | Post hoc exploratory |
| RQ4 | Output extension: rationale | Grader's own recorded score | Score–rationale contradictions and coverage per score-blind instrument | Exploratory |

Detailed evaluation design retained from article 8caf0b9. P1 is the primary analysis; S1–S6 are the secondary analyses, including replication and descriptive roles. Agreement means agreement with the teacher label; QWK means quadratic weighted kappa. Statistical roles do not imply that all analyses were computed: S4 remains uncomputed; S2/S6 were computed late, with qualifications in [A.4.6](../04-methods.md#a46).
