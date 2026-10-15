# A.7 Scope and provenance

[Appendix index](README.md)

<a id="a71"></a>

## A.7.1 Scope of the supplementary evidence

All responses stem from one bachelor-level course on Git and version control, with nine short-answer questions, answers in German, English prompt templates, and binary labels from one teacher. Agreement was measured on held-out responses to the same questions, graded with examples from the same teacher, not on new questions. Responses from this course were examined in both predecessor studies, and the pool of this article was examined repeatedly while its analyses were developed, which increases the risk that some analytic choices fit this pool. The results therefore do not transfer to other teachers, subjects, languages, item types, or providers without a new evaluation, which is the situation that the re-evaluation process of Section 6.2 of the article addresses. The model rankings, as in the ICWE paper, are a snapshot of their evaluation dates.

<a id="a72"></a>

## A.7.2 Component identity and traceability

Table [A.13](07-provenance.md#table-a13) summarizes how far this article meets the requirements of Section 3.1 of the article for each kind of change. All component comparisons draw from the same 450-row response pool (R3), and independent coder agreement uses its 439 distinct question–answer texts, but each change touches a different interface of the architecture. A stability baseline (R4) exists for the serving substitution and, through reruns, for part of the model set, but not for the decision component, the rationale audit, or the partial-credit grades. The run records (R6) pin the model identifier, the decoding settings, and, except for the original base runs, the prompt. They do not consistently pin inference engines, quantization, model revisions, or provider routes: some records contain such fields, for example the resolved upstream providers and returned snapshots of the replication gate (all calls of one model, samples of 60 calls for the others), the weight revisions of the two models run in September, and the engine versions of the rationale judges, while the hosted P1 arm lacks verified weight identity and provider-route provenance. A logging layer that is meant to support re-evaluation would therefore have to record not only what a single call needs for traceability but also which concrete component served it.

<a id="a73"></a>

## A.7.3 Provenance gaps and requirement coverage

*Provenance.* Several records are incomplete, and the affected results are reported together with their gaps. The script that produced the recorded P1 values was not found, although recomputation from the pinned prediction files reproduces them exactly; the raw outputs of the repeat controls of the P1 amendment are lost, so their discordances are quoted rather than recomputed; the four original on-premises base runs, among them the local arm of the first P1 run, have no recorded prompt hash; the ICWE runs recorded only alias identifiers of the hosted models; and a later acquisition of further hosted counterparts remained incomplete and is not used.

<a id="table-a13"></a>

### Table A.13

| Change | Affected interface | Reference (R1, R2) | Stability baseline (R4) | Blind reading (R5) | Records (R6) |
| --- | --- | --- | --- | --- | --- |
| Model set | Model adapter and backend | partial: teacher label, anchored; binary arms also against the independent reference (post hoc) | partial: reruns of four on-premises arms and one hosted arm | n.a. | partial: ICWE runs with alias identifiers only; four runs without prompt hash; gate run with resolved providers and snapshots |
| Serving path | Model adapter and backend | partial: teacher label, anchored | partial: API repeat controls, raw outputs lost | n.a. | partial: no weight revision, snapshot, or route of the hosted arm |
| Decision component | Adapter and typed output contract | partial: teacher label, anchored | no: one example selection per count, no repeat | n.a. | partial: returned snapshot recorded; comparators from earlier runs |
| Rationale | Output contract and review display | yes: own recorded score (consistency only) | no | yes; no human check | partial: Qwen judge revision not pinned |
| Partial credit | Output contract, validation, and analysis | yes: independent model-blind reference, adjacent disagreements as residual dissent | no: one run per model | n.a. | partial: no weight revision or engine version |

Requirements per kind of change and their status in this article. All component comparisons draw from the same 450-row response pool (R3); independent coder agreement uses its 439 distinct question–answer texts. yes: met; partial: met with the stated gap; no: not met; n.a.: not applicable.

[Download CSV](tables/table-a13.csv)
