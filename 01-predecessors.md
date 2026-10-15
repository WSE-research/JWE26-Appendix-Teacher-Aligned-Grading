# A.1 Predecessor results

[Appendix index](README.md)

<a id="a11"></a>

## A.1.1 ICWE protocol and predecessor results

Together with the architecture, the conference paper introduced a fold-wise train-size sweep protocol that varies the number of teacher-rated in-context examples from 0 to 40 under five-fold cross-validation. It evaluated five LLMs, all accessed through one hosted API, on 450 responses to nine short-answer questions of a bachelor-level computer science course on Git, each paired with a binary teacher rating [\[10\]](references.md#ref-Gwozdz2026ICWE). The evaluation was offline: it simulated incremental teacher feedback over fold splits of a fixed response pool rather than observing the adaptation loop in live teacher interaction.

For its first question, agreement at 40 examples exceeded agreement without examples for all five models, by between 1.56 and 18.44 percentage points. At the protocol ceiling of 40 examples, the highest observed teacher-aligned accuracy was 90.67%, reached by Claude Haiku 4.5, against a majority-class baseline of 56.0%, and the three best models were statistically indistinguishable at this protocol ceiling [\[10\]](references.md#ref-Gwozdz2026ICWE). For its second question, the required feedback volume was strongly model-dependent: Claude Haiku 4.5 first reached 90% with 10 examples, DeepSeek V3.2 with 30, and the remaining three models did not reach 90% within the evaluated range. The paper therefore recommended treating the teacher-feedback budget as a model selection parameter rather than as a fixed global constant, and it complemented agreement with, among other measures, false-pass and false-fail profiles, parse reliability, and token cost [\[10\]](references.md#ref-Gwozdz2026ICWE).

<a id="a12"></a>

## A.1.2 Related ICALT audit

A related audit, published at ICALT 2026, evaluated nine LLM graders under two prompt variants on 1,056 reviewed responses from the same course; eight of the graders were accessed through APIs, and one open-weight model was served locally with vLLM [\[9\]](references.md#ref-Gwozdz2026ICALT). Its human reference came from a manual review in which raters accepted or corrected decisions proposed by the course’s operational auto-grader. The paper therefore treated this reference as a pragmatic baseline that may be anchored by the proposed decision, not as blinded grading from scratch [\[9\]](references.md#ref-Gwozdz2026ICALT). Both predecessor studies grade binary correctness.
