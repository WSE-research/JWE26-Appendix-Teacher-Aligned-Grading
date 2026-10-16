# Table A.13: Requirements and provenance coverage

| Change | Affected interface | Reference (R1, R2) | Stability baseline (R4) | Blind reading (R5) | Records (R6) |
| --- | --- | --- | --- | --- | --- |
| Model set | Model adapter and backend | partial: teacher label, anchored; binary arms also against the independent reference (post hoc) | partial: reruns of four on-premises arms and one hosted arm | n.a. | partial: ICWE runs with alias identifiers only; four runs without prompt hash; gate run with resolved providers and snapshots |
| Serving path | Model adapter and backend | partial: teacher label, anchored | partial: API repeat controls documented in execution records; prediction CSVs unrecovered | n.a. | partial: no weight revision, snapshot, or route of the hosted arm |
| Decision component | Adapter and typed output contract | partial: teacher label, anchored | no: one example selection per count, no repeat | n.a. | partial: returned snapshot recorded; comparators from earlier runs |
| Rationale | Output contract and review display | yes: own recorded score (consistency only) | no | yes; no human check | partial: Qwen judge revision not pinned |
| Partial credit | Output contract, validation, and analysis | yes: independent model-blind reference, adjacent disagreements as residual dissent | no: one run per model | n.a. | partial: no weight revision or engine version |

Requirements per kind of change and their status in this article. All component comparisons draw from the same 450-row response pool (R3); independent coder agreement uses its 439 distinct question–answer texts. yes: met; partial: met with the stated gap; no: not met; n.a.: not applicable.

[CSV](table-a13.csv) · [Context](../07-provenance.md#table-a13)
