# A.5 Supplementary results for RQ1 and RQ2

[Appendix index](README.md)

[A.5.1 Data availability](05-teacher-alignment.md#a51) · [A.5.2 Teacher alignment of the extended model set](05-teacher-alignment.md#a52) · [A.5.3 Teacher feedback volume for the extended model set](05-teacher-alignment.md#a53)

<a id="a51"></a>

## A.5.1 Data availability

Table [A.5](05-teacher-alignment.md#table-a5) lists the data on which each comparison rests, with missing and unusable cases as separate states. All 51 model prediction artifacts of the run selection grade the same 450 rows at 40 examples, which hold 439 unique question–answer texts in 45 prompt clusters of ten rows, and they share identical teacher labels, so agreement values at 40 examples differ in their denominators only where outputs are missing. Missing decisions are rare: among the 15 base arms, only Qwen3.8 Flash lost outputs, six requests that failed with a client error, and among the remaining 36 artifacts, two outputs of Qwen3.8-27B under a deconfounding prompt and one Phi-4 output under the rationale prompt cannot be parsed. The fifth model of the currency tier, GLM-5.3 Flash, planned as the successor of GLM-4.7 Flash, could not be measured under the study settings and has no arm. Both runs of the serving comparison yielded parseable outputs for all 450 rows in both arms, and the full-grid runs used for RQ2 of the article yielded 450 parseable outputs at every example count. The decision component returned usable decisions for all 1,800 calls; three level answers whose probabilities did not sum exactly to one were kept with flags. The independent human reference is complete, with all 439 texts coded by each coder, and the rationale audit lacks one rationale, the unparseable Phi-4 output. An additional OpenRouter acquisition of further hosted counterparts and repeat controls stopped incomplete, with 1,807 valid answers, 1,341 unattempted tasks, and two attempts without a valid answer; it is not used in this article.

<a id="table-a5"></a>

### Table A.5: Data availability and missing cases

| Comparison | Collection | Valid and missing cases |
| --- | --- | --- |
| Agreement of the base arms (RQ1 of the article) | 15 arms $`\times`$ 450 rows | 14 arms 450 parseable; Qwen3.8 Flash 444 (6 failed requests); GLM-5.3 Flash not measurable |
| Further conditions and controls (RQ1 of the article) | 36 artifacts $`\times`$ 450 rows | 3 unparseable outputs (2 Qwen3.8-27B, deconfounding prompt; 1 Phi-4, rationale prompt) |
| Serving substitution P1 (RQ1 of the article) | 2 runs $`\times`$ 2 arms $`\times`$ 450 rows | all 1,800 outputs parseable; 450 pairs per run |
| Decision component (RQ1 of the article) | 4 example counts $`\times`$ 450 calls | 1,800 usable; 3 flagged probability sums |
| Feedback curves, full grid (RQ2 of the article) | 11 runs $`\times`$ 11 counts $`\times`$ 450 rows; ICWE: 5 models $`\times`$ 11 $`\times`$ 450 | all cells 450 parseable |
| Feedback, currency tier (RQ2 of the article) | 4 models $`\times`$ 4 counts $`\times`$ 450 rows | Qwen3.8 Flash 445, 444, 447, 444 parseable; others 450 |
| Partial credit, models (RQ3 of the article) | 4 runs $`\times`$ 450 rows | all 1,800 outputs parseable |
| Partial credit, humans (RQ3 of the article) | 2 coders $`\times`$ 439 unique texts | 439 of 439 per coder; 71 distances $`\geq 2`$ adjudicated; 152 distance-1 cases residual dissent |
| Rationale audit (RQ4 of the article) | 4 runs $`\times`$ 450 rationales | 1 missing (Phi-4); 1,799 judgments per judge |
| Supplementary OpenRouter acquisition | not used | 1,807 valid, 1,341 unattempted, 2 failed attempts; incomplete |

Data available per comparison. Rows are target rows of the 450-row pool at 40 in-context examples unless stated otherwise; missing or unusable cases remain visible as separate states. The binary human-reference comparison includes stored fallback zeros as documented in [A.6.1](06-human-reference.md#a61).

[Download CSV](tables/table-a5.csv)

<a id="a52"></a>

## A.5.2 Teacher alignment of the extended model set

<a id="a521"></a>

### A.5.2.1 Replication gate and agreement at 40 examples

The replication gate decides whether the ICWE results and the new results may be combined. Rerun under the harmonized settings, the five hosted ICWE models reproduced their ICWE agreement at 40 examples within the tolerance of three percentage points (Table [A.6](05-teacher-alignment.md#table-a6)): the differences range from $`-2.00`$ points for Gemini 2.5 Flash-Lite to $`+0.89`$ points for GLM-4.7 Flash, so the gate passes and the gate runs enter the joint comparison below. The lower Gemini 2.5 Flash-Lite point estimate recurred in a repeat run, which reached 83.56%, $`2.44`$ points below the ICWE value, and disagreed with the gate run on 8 of 450 rows; the gate passes because the offset is smaller than the tolerance, not because it is indistinguishable from zero. The exact reproduction for Qwen3.5-397B-A17B is partly a matter of routing: OpenRouter distributed its calls over ten upstream providers whose agreement ranged from 82.8% to 100.0%. The 100.0% belongs to the 32 calls served by GMICloud, which returned reasoning tokens despite the disabled reasoning setting; without these calls, the gate run agrees on 370 of 418 rows (88.52%), against 372 of the same 418 rows (89.00%) in the ICWE run, a difference of $`-0.48`$ points, still within the tolerance. Whether the hosted models themselves changed since the predecessor evaluation cannot be checked, because the ICWE runs recorded only alias identifiers; the gate also spans a change of settings from an initial output-token budget of 250 with a response-format constraint to an initial budget of 512 without it (parse retries could increase both budgets).

<a id="table-a6"></a>

### Table A.6: ICWE replication gate

| Model | ICWE run | Gate run | Diff. (pp) | Within $`\pm 3`$ |
| --- | --- | --- | --- | --- |
| Claude Haiku 4.5 | 90.67 | 91.11 | $`+0.44`$ | yes |
| DeepSeek V3.2 | 90.00 | 89.78 | $`-0.22`$ | yes |
| Qwen3.5-397B-A17B | 89.33 | 89.33 | $`0.00`$ | yes |
| Gemini 2.5 Flash-Lite | 86.00 | 84.00 | $`-2.00`$ | yes |
| GLM-4.7 Flash | 81.78 | 82.67 | $`+0.89`$ | yes |
| Gemini 2.5 Flash-Lite, repeat | 86.00 | 83.56 | $`-2.44`$ | (control) |

Replication gate S3: agreement with the teacher label (%) of the five hosted ICWE models at 40 examples on the same 450 rows, in the ICWE run from the predecessor evaluation (initial output-token budget 250, response-format constraint) and in the gate run under harmonized settings (initial budget 512, no constraint; parse retries could increase both budgets); both through OpenRouter at temperature 0.2. The criterion is a difference within $`\pm 3`$ percentage points. The last row is a repeat of the Gemini 2.5 Flash-Lite gate run, reported as a control.

[Download CSV](tables/table-a6.csv)

<a id="table-a7"></a>

### Table A.7: Teacher alignment and overruled/confirmed rows

|  | All rows |  | ICWE | Overruled | Confirmed |
| --- | --- | --- | --- | --- | --- |
| Model | % ($`k/n`$) | 95% Wilson | % | $`k/43`$ (%) | % ($`k/n`$) |
| *On premises, original roster (vLLM)* |  |  |  |  |  |
| Qwen3.6-27B | **91.11** (410/450) | \[88.12, 93.40\] |  | 32 (74.42) | 92.87 (378/407) |
| Qwen3.8-27B | 89.56 (403/450) | \[86.39, 92.05\] |  | 33 (76.74) | 90.91 (370/407) |
| Phi-4 | 89.11 (401/450) | \[85.90, 91.66\] |  | 20 (46.51) | 93.61 (381/407) |
| Mistral Small 3.2 24B | 85.78 (386/450) | \[82.25, 88.70\] |  | 13 (30.23) | 91.65 (373/407) |
| *On premises, added later (vLLM)* |  |  |  |  |  |
| Qwen3-32B | 90.67 (408/450) | \[87.62, 93.02\] |  | 27 (62.79) | 93.61 (381/407) |
| Qwen3.5-27B | 90.22 (406/450) | \[87.13, 92.64\] |  | 34 (79.07) | 91.40 (372/407) |
| *Hosted, ICWE models in the gate run (OpenRouter)* |  |  |  |  |  |
| Claude Haiku 4.5 | **91.11** (410/450) | \[88.12, 93.40\] | 90.67 | 31 (72.09) | 93.12 (379/407) |
| DeepSeek V3.2 | 89.78 (404/450) | \[86.63, 92.25\] | 90.00 | 26 (60.47) | 92.87 (378/407) |
| Qwen3.5-397B-A17B | 89.33 (402/450) | \[86.14, 91.86\] | 89.33 | 31 (72.09) | 91.15 (371/407) |
| Gemini 2.5 Flash-Lite | 84.00 (378/450) | \[80.33, 87.10\] | 86.00 | 32 (74.42) | 85.01 (346/407) |
| GLM-4.7 Flash | 82.67 (372/450) | \[78.90, 85.88\] | 81.78 | 20 (46.51) | 86.49 (352/407) |
| *Hosted, currency tier (OpenRouter)* |  |  |  |  |  |
| Qwen3.8 Flash$`^{\ddagger}`$ | 90.54 (402/444) | \[87.46, 92.93\] |  | 34 (79.07) | 91.77 (368/401) |
| Gemini 3.5 Flash-Lite$`^{\dagger}`$ | 90.44 (407/450) | \[87.38, 92.83\] |  | 30 (69.77) | 92.63 (377/407) |
| GPT-5.6 Luna$`^{\ast}`$ | 90.00 (405/450) | \[86.88, 92.44\] |  | 31 (72.09) | 91.89 (374/407) |
| DeepSeek V4 Flash | 86.44 (389/450) | \[82.97, 89.30\] |  | 27 (62.79) | 88.94 (362/407) |
| GLM-5.3 Flash | not measurable under the study settings |  |  |  |  |
| *Reference lines (S5)* |  |  |  |  |  |
| Majority class | 56.00 (252/450) |  |  | 8 (18.60) | 59.95 (244/407) |
| Incumbent reference | 90.44 (407/450) |  |  | 0 (0.00) | 100.00 (407/407) |
| Constant “incorrect” |  |  |  | 35 (81.40) |  |

Agreement with the teacher label of the 15 binary base arms at 40 in-context examples (one run per model, base prompt, temperature 0.2 requested), on parseable rows, with 95% Wilson intervals; bold: highest. ICWE: agreement in the ICWE run from the predecessor evaluation, which each gate run must reproduce within $`\pm 3`$ percentage points (S3). Overruled: the 43 rows on which the lecturer overruled the operational grader; confirmed: the 407 rows on which the lecturer confirmed it (S6, descriptive). Reference lines (S5): the majority class always decides “correct”, the incumbent-agreement reference (incumbent reference) reproduces the operational grader, and a constant “incorrect” decision is shown beside the overruled column. $`^{\ast}`$Requested temperature discarded by the model’s endpoints; run at the model’s default temperature. $`^{\dagger}`$Run with the minimal instead of the disabled reasoning setting, which the model rejects. $`^{\ddagger}`$Six failed requests; counting their stored fallback scores of 0 gives 406 of 450 rows (90.22%), treating every failed request as a disagreement with the teacher label gives 402 of 450 (89.33%).

[Download CSV](tables/table-a7.csv)

The decisive line, however, is the incumbent-agreement reference, called the anchoring ceiling in the first version of the analysis plan: reproducing the operational grader’s decision agrees with the teacher label on 407 of 450 rows (90.44%), because the lecturer confirmed that decision on all but 43 rows. Four arms lie above this line on their parseable rows, Qwen3.6-27B and Claude Haiku 4.5 with 410, Qwen3-32B with 408, and Qwen3.8 Flash with 402 of 444 rows, and Gemini 3.5 Flash-Lite equals it with 407; the largest margin is three rows. For Qwen3.8 Flash, the position depends on how its six failed requests are counted: with their stored fallback scores, it agrees on 406 of 450 rows, and with every failed request treated as a disagreement with the teacher label, on 402 of 450, both below the line. The Wilson intervals of the eleven highest arms all contain 90.44%, whereas those of the four lowest arms (DeepSeek V4 Flash, Mistral Small 3.2, Gemini 2.5 Flash-Lite, and GLM-4.7 Flash) lie entirely below it. The best arms thus exceed the incumbent-agreement reference by only three of 450 rows; their marginal Wilson intervals contain the reference value, and no paired superiority or equivalence analysis against the incumbent is reported. An agreement near 90% on this pool mostly measures agreement with the operational grader, and whether a model is better than that grader cannot be read from the overall agreement.

<a id="a522"></a>

### A.5.2.2 Overruled and confirmed rows (S6)

S6 separates the 407 rows on which the lecturer confirmed the operational grader from the 43 rows on which the lecturer overruled it. On the confirmed rows, where the teacher label equals the operational decision, the arms agree on between 85.01% (Gemini 2.5 Flash-Lite) and 93.61% (Qwen3-32B and Phi-4). On the overruled rows, they agree on between 13 (Mistral Small 3.2) and 34 (Qwen3.5-27B and Qwen3.8 Flash) of 43, and arms with almost the same overall agreement differ widely there: Qwen3.5-27B and Qwen3-32B are two rows apart overall (406 and 408 of 450) but seven rows apart on the overruled rows (34 and 27 of 43). These differences do not show that some models detect the operational grader’s errors. Of the 43 overruled rows, 35 carry the label “incorrect”, whereas 59.95% of the confirmed rows carry the label “correct”, so a constant decision of “incorrect” agrees on 81.40% of the overruled rows, more than any arm (at most 34 of 43, 79.07%), and a grader that decides more strictly overall gains on these rows; the analysis plan therefore rules out reading this column as error detection. The column is also coarse: at 43 rows, a 95% Wilson interval has a half-width of about 13 points at an agreement of 75%, and the intervals range, for example, from 64.8% to 88.6% for Qwen3.5-27B and from 18.6% to 45.1% for Mistral Small 3.2. The prespecified Fisher exact tests for the two new models were computed after their descriptive values had been reported (family size two): Qwen3-32B agrees on 27/43 overruled and 381/407 confirmed rows (62.79% versus 93.61%, Holm p < 0.001); Qwen3.5-27B agrees on 34/43 and 372/407 (79.07% versus 91.40%, Holm p = 0.025). A within-cluster permutation sensitivity gives p = 0.047 for Qwen3.5-27B, making this result borderline. Both models remain below the constant-incorrect reference on the overruled subset. The split remains exploratory for the four original models from which the hypothesis was generated; it does not show error detection. [Test outputs and provenance](reproduction/secondary-tests/README.md).

<a id="a523"></a>

### A.5.2.3 Prompt conditions, paired comparisons, and repeat runs

S1 replicates, within each of the four original on-premises models, the comparison of the guided prompt with the base prompt (family size four). The guided prompt lowered agreement with the teacher label in all four models: from 91.11% to 87.33% for Qwen3.6-27B, from 89.56% to 84.44% for Qwen3.8-27B, from 89.11% to 78.44% for Phi-4, and from 85.78% to 84.44% for Mistral Small 3.2. The discordant rows were one-sided for the first three models (25 rows on which only the base prompt agreed against 8 on which only the guided prompt agreed, 27 against 4, and 70 against 22) and nearly balanced for Mistral Small 3.2 (41 against 35). With the cluster-robust p-values that the plan prescribes for the 45 prompt clusters, Holm-adjusted within the family, the p-values lie below 0.05 for Qwen3.6-27B ($`p = .0090`$), Qwen3.8-27B ($`p = .0039`$), and Phi-4 ($`p = .0012`$) but not for Mistral Small 3.2 ($`p = .6249`$); exact McNemar tests that treat the rows as independent lead to the same decisions (Holm-adjusted $`p = .0091`$, $`.0001`$, $`< .0001`$, and $`.567`$). Because an earlier experiment had compared the same prompts under a different protocol, S1 is a replication rather than a first test. Exploratory deconfounding conditions, run afterwards on the same models, attribute most of the loss in the three affected models to the completeness rubric of the guided prompt rather than to its omission of the instruction to use the examples.

S2 was computed late from the six declared on-premises base arms against Claude Haiku 4.5 (410/450, 91.11%). Paired differences range from −5.33 to 0.00 percentage points. With cluster sign-flip permutation over 45 prompt clusters, none rejects after Holm correction (K=6; all adjusted p ≥ 0.211). Exact McNemar rejects only Mistral Small 3.2 (adjusted p = 0.043). Because the extension of the cluster convention and the reference-run designation were recorded after descriptive results were known, both tests are reported ([A.4.6](04-methods.md#a46)). No equivalence margin was declared for S2, so non-rejection does not establish equivalence or substitutability. [Full paired counts, intervals and p-values](reproduction/secondary-tests/s2_onprem_vs_claude_haiku.csv).

The remaining prompt conditions are exploratory. Under the partial-credit prompt, whose binary decision field is evaluated here and whose levels Section 5.3 compares with the human reference, the four original models agreed with the teacher label on 416 (Qwen3.6-27B), 404 (Qwen3.8-27B), 398 (Phi-4), and 389 (Mistral Small 3.2) of 450 rows; these runs also serve as comparators of the component substitution in Section 5.1.2. The rationale condition is analyzed in Section 5.4, and the per-arm agreement of the rationale and the three deconfounding conditions is part of the archived per-arm output of the analysis.

The reproducibility checks show the observed differences between the original runs and reruns under the committed evaluation code. The reruns of the four original on-premises base arms with the committed evaluation code disagreed with the original runs on 3 (Phi-4), 7 (Mistral Small 3.2), 8 (Qwen3.6-27B), and 11 (Qwen3.8-27B) of 450 rows, which changed agreement by $`-0.22`$, $`-1.56`$, $`-0.44`$, and $`+0.67`$ points (rerun minus original); the original runs remain the basis of S1. The repeat of the Gemini 2.5 Flash-Lite gate run disagreed with the gate run on 8 rows, and the plan amendment for P1 records 12 of 450 discordant rows between two API runs of Mistral Small 3.2 at temperature 0.2. Most differences between neighboring arms in Table [A.7](05-teacher-alignment.md#table-a7), including every margin above the incumbent-agreement reference, are of this size. At temperature 0, which the plan reserves for P1 and the runs that measure its operating point, Qwen3.6-27B, Qwen3.8-27B, and Phi-4 agreed with the teacher label on 409, 406, and 400 of 450 rows (90.89%, 90.22%, and 88.89%), and a repeat of the Qwen3.8-27B run reached the same 406 rows while disagreeing with it on 2 rows; these values form a stratum of their own and are not compared with the arms at temperature 0.2.

<a id="a524"></a>

### A.5.2.4 Serving substitution (P1)

P1, the only prespecified primary test, asks whether serving the same open-weight model on premises instead of through a hosted API changes its agreement with the teacher label, the comparison that the ICWE study could not make because all of its calls ran through one hosted API (L3). Its two arms are the same nominal release of Mistral Small 3.2, served from the published weights on the local vLLM server and requested through OpenRouter. That the hosted route serves identical weights is an assumption of the design, not a finding: the run records name the model, the endpoint, and the decoding settings, but contain no weight revision, snapshot, or fingerprint, and there is no routing evidence for the hosted arm. Both arms grade the same 450 rows with the base prompt and 40 examples and are paired on question, fold, student, and answer text (Section 4.5 of the article); equivalence requires the 90% bootstrap interval of the paired difference to lie within $`\pm 3.0`$ percentage points.

The first run, at temperature 0.2 as originally planned, did not establish equivalence. The locally served model agreed with the teacher label on 85.78% of the rows and the API-served model on 83.78%; the paired difference of $`+2.00`$ percentage points had a 90% bootstrap confidence interval from $`+0.44`$ to $`+3.56`$ points, whose upper end exceeds the margin. The two arms decided 17 rows differently, 13 of them in line with the teacher label only on premises and 4 only through the API, and McNemar’s exact test gave $`p = 0.049`$.

The analysis plan had specified no repeat control for this comparison. Measured afterwards, two runs of the API arm at temperature 0.2 disagreed with each other on 12 of 450 rows, which is of the same order as the 17 rows on which the two serving paths disagreed. The documented plan amendment D10, made with knowledge of the first result, therefore classified the first run as inconclusive rather than as evidence of a serving effect and moved both arms to temperature 0, where two runs of the API arm disagreed on 3 of 450 rows.

In the rerun at temperature 0, the locally served model agreed with the teacher label on 84.67% of the rows and the API-served model on 84.00%. The paired difference of $`+0.67`$ percentage points has a 90% bootstrap confidence interval from $`-0.67`$ to $`+2.00`$ points, which lies entirely within the margin, so equivalence is established at this operating point; the arms decided 13 rows differently (8 in line with the teacher label only on premises, 5 only through the API), and McNemar’s exact test gives $`p = 0.581`$. A post hoc cluster bootstrap over the 45 question–fold clusters, which is not part of the prespecified test, leaves both conclusions unchanged, with intervals from $`-0.67`$ to $`+2.00`$ points for the rerun and from $`+0.44`$ to $`+3.33`$ points for the first run. Because the operating point was changed after the first result was known, the equivalence carries less confirmatory weight than a result at the originally fixed operating point would; each run compares the two arms at one temperature, and the two runs are not compared with each other.

The later analysis script `31_jwe_n40_agreement.py` reproduces the agreement values, paired differences, discordant-pair counts, item-bootstrap intervals, and McNemar results of both P1 comparisons from pinned prediction files. It is a reconstruction; the original analysis invocation and its output file have not been recovered. The cluster-bootstrap intervals were added as a post hoc sensitivity analysis.

Historical execution records preserve the launch commands, comparison code and successful output of the four API repeat controls. Each loaded 450 rows; the two temperature-0.2 controls disagreed on 12 scores and the two temperature-0 controls on 3. Their underlying prediction CSVs have not been recovered, so these counts have not been recomputed from those files. Permanent loss has not been established. The [repeat-control evidence summary](reproduction/p1-repeat-controls.md) distinguishes this historical calculation from the separate P1 reconstruction. The local arm of the first run is the original Mistral base run from the original evaluation, for which no prompt hash was recorded. Finally, the weight identity of the two arms rests on the design assumption stated above, without routing evidence for the hosted arm.

<a id="a525"></a>

### A.5.2.5 Exploratory component substitution

The component substitution replaces the LLM grader by the decision component Jev (Section 4.4) and compares its binary decisions with the teacher label on the same 450 rows at 0, 5, 20, and 40 examples. Its comparators are the stored binary decisions of the four partial-credit runs at the same example counts, which ran at temperature 0.2, so every comparison is paired by row and example count but compares whole components rather than models. The substitution was added after the analysis plan, and its continuation was planned before its new calls but after the first results on the same answers had been inspected; all results of this subsection are exploratory. Because a different number of examples also means a different selection of examples, differences between example counts are not pure effects of the count.

Jev agreed with the teacher label on 399, 401, 408, and 408 of 450 rows at 0, 5, 20, and 40 examples, that is, on 88.67% to 90.67% (Table [A.8](05-teacher-alignment.md#table-a8)). At 40 examples, the four comparators agreed on between 389 (Mistral Small 3.2, 86.44%) and 416 rows (Qwen3.6-27B, 92.44%); Jev lies 1.78 points below Qwen3.6-27B, with a nine-question cluster-bootstrap 95% interval from $`-6.00`$ to $`+2.22`$ points, and one row above the incumbent-agreement reference. Between 20 and 40 examples, Jev’s point agreement did not change; the 95% question-cluster bootstrap interval of the paired difference, from $`-2.00`$ to $`+2.00`$ points, shows neither a difference nor equivalence, and the observed API bill at 20 examples was 40.2% lower than at 40. On the 437 rows whose answer text does not occur among the in-context examples at any count, Jev agreed on 88.33% to 90.39%, with the same ordering across example counts. Fitting Jev’s binary decision threshold per held-out question instead of using the fixed threshold of 0.5 lowered its agreement at 40 examples to 391 of 450 rows (86.89%), so the fixed threshold was kept.

<a id="table-a8"></a>

### Table A.8: Exploratory Jev component substitution

|  | Jev |  | Qwen3.6-27B | API bill |
| --- | --- | --- | --- | --- |
| Examples | 450 rows | 437 overlap-free | 450 rows | (USD) |
| 0 | 399 (88.67) | 386 (88.33) | 87.56 | 0.0100 |
| 5 | 401 (89.11) | 388 (88.79) | 91.78 | 0.0149 |
| 20 | 408 (90.67) | 395 (90.39) | 92.67 | 0.0305 |
| 40 | 408 (90.67) | 395 (90.39) | 92.44 | 0.0510 |
| Majority class | 252 (56.00) |  |  |  |
| Incumbent reference | 407 (90.44) |  |  |  |

Exploratory component substitution: agreement with the teacher label by number of in-context examples, as matching rows (%). Jev ran with its service defaults; the comparator is the stored binary decision of the Qwen3.6-27B partial-credit run at temperature 0.2 on the same rows. The overlap-free column uses the 437 rows whose answer text does not occur among the in-context examples at any count. The API bill is the observed provider charge for 450 Jev calls, rounded to four decimals. The reference lines (S5), the majority class and the incumbent-agreement reference (incumbent reference), are the same at every example count.

[Download CSV](tables/table-a8.csv)

For selective automation at 40 examples, the referral thresholds were fitted on eight questions and evaluated on the ninth, rotating over all nine; only the fitting of the policy excludes the held-out question, because the grader still receives examples of the same question. With training error targets of 2%, 5%, and 10%, the policies accepted 252, 375, and 445 of the 450 rows (coverage of 56.00%, 83.33%, and 98.89%), with an agreement of 98.02%, 94.67%, and 90.79% among the accepted rows. The 5% target was missed with a held-out error of 5.33%, and when the overlapping rows were removed from fitting and testing, the 2% target was missed as well, with 5 errors among the 203 accepted of 437 rows (2.46%). The targets are therefore empirical settings of the policy, not guarantees for future rows.

In a simulated cascade, the rows that the held-out threshold did not accept took the stored decision of the Qwen3.6-27B partial-credit run. The cascade agreed with the teacher label on 414 of 450 rows (92.00%) and routed 78 rows (17.33%) to the stored LLM decision, whereas the LLM alone agreed on 416 rows (92.44%); on the 437 overlap-free rows, the cascade agreed on 401 (91.76%) with 78 routed rows. The two components err on partly different rows: 19 errors are shared, Jev alone is right on 15 rows, and Qwen3.6-27B alone on 23, so even an oracle that always chose the right component would be bounded by 431 of 450 rows (95.78%), an upper bound rather than an available policy. A fixed threshold of 0.6, chosen after all thresholds had been inspected on the full data, would have reached 418 of 450 rows (92.89%) with 48 routed rows; because it was selected on the evaluation data, it is a post-selection value and not an estimate of held-out performance.

These results come from offline simulations with stored decisions, not from a deployed service. The 82.67% fewer Qwen3.6-27B decisions of the cascade are counted decisions, not measured savings in cost or latency, and the API bill is the provider charge of the decision component, not a total or hardware-normalized cost. Qwen3.6-27B was chosen as the cascade partner because it had been the best comparator in an earlier inspection of the same rows, which favors the cascade. The evidence is further bounded by nine questions, comparator outputs produced under other conditions, the inherited text overlap, a single example selection per count, and the repeated examination of this dataset; it does not support statements about other courses or teachers or about an educational benefit.

<a id="a53"></a>

## A.5.3 Teacher feedback volume for the extended model set

RQ2 of the article repeats the threshold analysis of the ICWE paper for the extended model set: the number of in-context teacher examples at which agreement with the teacher label first reaches 85%, 88%, and 90%, and, added in this article, the number from which it stays at or above 85% and 90% at every larger count (Section 4.5 of the article). All results in this subsection are exploratory; as in the ICWE paper, each value comes from one run without an interval on the attainment, and each agreement value is computed on the parseable rows from the 450-row pool at one example count.

As a precondition for every new value, the analysis reproduced the ICWE results from the archived ICWE predictions from the predecessor evaluation: the attainment values of the ICWE paper’s Table 3 and the agreement at 0 and 40 examples of its Table 1 match exactly for all five models (Table [A.9](05-teacher-alignment.md#table-a9)). The added columns show that several published attainments are transient. Claude Haiku 4.5 first reaches 90% at 10 examples but stays at or above 90% only from 40, and DeepSeek V3.2 reaches 90% at 30 and stays there only from 40. Gemini 2.5 Flash-Lite stays at or above 85% only from 40 examples, and GLM-4.7 Flash never stays there, the transient attainment that the ICWE paper already noted.

Threshold attainment requires the full grid of eleven example counts. Among the new runs with the base prompt, this grid exists for the four original on-premises models, for their four reproducibility reruns, and for the three further runs of the serving comparison. The five ICWE models were rerun at 40 examples only, for the replication gate, and the two on-premises models added later were also run at 40 examples only, so the analysis plan admits no learning curve, saturation claim, or comparison with zero examples for them. The currency tier was run at four example counts, which yields a coarse trajectory but no attainment comparable with the full grid.

Among the on-premises models at temperature 0.2, Qwen3.6-27B reaches 85% without examples, 88% at 3, and 90% at 5 examples (Tables [A.9](05-teacher-alignment.md#table-a9) and [A.10](05-teacher-alignment.md#table-a10)), and it stays at or above 90% at every larger count; its rerun reaches the three targets at 1, 1, and 5 examples. Qwen3.8-27B starts lowest of the four, at 76.22% without examples, reaches 85% and 88% at 3 and 90% at 10 examples, but falls below 90% again, to 89.78% at 20 and 89.56% at 40 examples; its rerun reaches the targets at 3, 5, and 10 examples and stays at or above 90% from 35. Phi-4 reaches 85% at 3 and 88% at 15 examples but never 90%, with a maximum of 89.11% at 40, and its rerun shows the same attainment. Mistral Small 3.2 starts at 86.00% without examples and falls below 85% once examples are added (82.67% with one and 79.11% with three examples), so the attainment of 85% at zero examples that the ICWE rule records is transient; the original run stays at or above 85% only from 35 examples, and its rerun never does.

Measured by the first attainment of 85%, the four on-premises models need between 0 and 3 examples, against 0 to 25 for the five ICWE models in the ICWE run. This contrast is not settings-identical: the ICWE curves ran through OpenRouter with an initial output-token budget of 250 and a response-format constraint, the new curves on premises with an initial budget of 512 and without the constraint (parse retries could increase both), and the replication gate establishes the reproduction of the ICWE values only at 40 examples. The Mistral attainment, moreover, is transient, as GLM-4.7 Flash’s was in the ICWE run. The reruns show that single-run attainment is fragile: under the same recorded decoding settings, using the committed evaluation code for the reruns, first attainment moved by one grid step for two of the four models (Qwen3.6-27B at 85% and 88%, Qwen3.8-27B at 88%), and whether a run stays above a target changed for Qwen3.8-27B at 90% and for Mistral Small 3.2 at 85%. Finally, the 90% target lies just below the incumbent-agreement reference of 90.44%, so reaching it mostly measures agreement with the operational grader rather than an improvement over it.

Over the full grid at temperature 0.2, the on-premises and API runs of the same nominal Mistral release differ by $`+0.89`$ points without examples and by $`+2.00`$ points at 40 examples (exploratory and not part of P1); the API run first reaches 85% without examples and never stays at or above it. At temperature 0, a stratum of its own, the local P1 arm first reaches 85% without examples (86.00%) and the API arm at 25 examples, and neither stays at or above 85%; at 40 examples, they reach 84.67% and 84.00%.

The four measured models of the currency tier were run at 0, 5, 20, and 40 examples. On this grid, Gemini 3.5 Flash-Lite agreed with the teacher label on 87.33%, 89.56%, 90.44%, and 90.44% of the rows, GPT-5.6 Luna on 86.89%, 89.11%, 89.33%, and 90.00%, Qwen3.8 Flash on 79.10%, 88.51%, 89.26%, and 90.54% of its 445, 444, 447, and 444 parseable rows, and DeepSeek V4 Flash on 81.33%, 83.33%, 85.11%, and 86.44%. GPT-5.6 Luna ran at its default temperature and Gemini 3.5 Flash-Lite with minimal reasoning, and GLM-5.3 Flash could not be measured. Because the grid omits seven of the eleven counts, these values describe the sampled points only and support neither an attainment comparable with Table [A.9](05-teacher-alignment.md#table-a9) nor a statement about the course between the points.

<a id="table-a9"></a>

### Table A.9: First and sustained feedback-target attainment

|  | First reaches |  |  | Stays from |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Model | 85% | 88% | 90% | 85% | 90% | $`n=0`$ | $`n=40`$ |
| *ICWE run (OpenRouter, ICWE settings)* |  |  |  |  |  |  |  |
| Claude Haiku 4.5 | 0 | 3 | 10 | 3 | 40 | 87.11 | 90.67 |
| DeepSeek V3.2 | 10 | 15 | 30 | 10 | 40 | 72.89 | 90.00 |
| Qwen3.5-397B-A17B | 5 | 10 | – | 5 | – | 81.11 | 89.33 |
| Gemini 2.5 Flash-Lite | 25 | – | – | 40 | – | 67.56 | 86.00 |
| GLM-4.7 Flash | 10 | – | – | – | – | 80.22 | 81.78 |
| *On premises, original base runs (vLLM)* |  |  |  |  |  |  |  |
| Qwen3.6-27B | 0 | 3 | 5 | 0 | 5 | 85.11 | 91.11 |
| Qwen3.8-27B | 3 | 3 | 10 | 3 | – | 76.22 | 89.56 |
| Phi-4 | 3 | 15 | – | 3 | – | 84.67 | 89.11 |
| Mistral Small 3.2 24B | 0 | – | – | 35 | – | 86.00 | 85.78 |
| *On premises, reproducibility reruns (vLLM)* |  |  |  |  |  |  |  |
| Qwen3.6-27B | 1 | 1 | 5 | 1 | 5 | 84.89 | 90.67 |
| Qwen3.8-27B | 3 | 5 | 10 | 3 | 35 | 77.11 | 90.22 |
| Phi-4 | 3 | 15 | – | 3 | – | 83.78 | 88.89 |
| Mistral Small 3.2 24B | 0 | – | – | – | – | 86.00 | 84.22 |
| *OpenRouter, first P1 API arm* |  |  |  |  |  |  |  |
| Mistral Small 3.2 24B | 0 | – | – | – | – | 85.11 | 83.78 |

Threshold attainment for the runs with all eleven example counts, all at temperature 0.2: the smallest number of in-context examples at which agreement with the teacher label first reaches 85%, 88%, and 90% (the rule of the ICWE paper’s Table 3), and the smallest number from which it stays at or above 85% and 90% at every larger count; “–” means not reached. The last two columns give agreement (%) without examples and with 40. The ICWE rows are recomputed from the archived ICWE predictions and equal the published values. Reference lines (S5) at every count: majority class 56.00%, incumbent-agreement reference 90.44%.

[Download CSV](tables/table-a9.csv)

<a id="table-a10"></a>

### Table A.10: Agreement over the full example-count grid

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

Agreement with the teacher label (%) by number of in-context examples $`n`$ for the runs of Table [A.9](05-teacher-alignment.md#table-a9), all at temperature 0.2, each cell on 450 parseable rows. ICWE: run from the predecessor evaluation through OpenRouter under the ICWE settings (Haiku 4.5: Claude Haiku 4.5; Gemini 2.5 FL: Gemini 2.5 Flash-Lite); on-prem.: original base runs from the original evaluation; rerun: reproducibility reruns from the reproducibility check; API: first P1 API arm. Reference lines (S5) at every $`n`$: majority class 56.00%, incumbent-agreement reference 90.44%.

[Download CSV](tables/table-a10.csv)
