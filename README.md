# Online appendix: Teacher-Aligned Grading in Web-Based Assessment

Supplementary methods, comparison details, aggregate results, figures, prompts and reproduction code for the accompanying Journal of Web Engineering article by Jonas Gwozdz and Andreas Both.

## Start here

- **Understand the study:** the [reviewer guide](REVIEWER_GUIDE.md) explains the two grading references, the scales, and which material supports each research question.
- **Inspect a result:** follow the question-to-evidence map below, or browse the [tables](tables/README.md) and [figures](figures/README.md).
- **Check the supplied material:** run the two Python commands below. Both work offline with the standard library, without credentials or student data.

The study contains **450 response records for nine questions, representing 439 distinct question–answer texts**. Historical teacher labels, new independent human ratings, and a grader's own recorded score serve different comparison purposes. They are not interchangeable references.

| Question | Evidence in this appendix |
|---|---|
| RQ1: agreement with historical teacher labels after component changes | [Replication gate and model comparison](05-teacher-alignment.md#a521), [serving comparison](05-teacher-alignment.md#a524), [decision-component comparison](05-teacher-alignment.md#a525) |
| RQ2: examples needed to reach and maintain agreement targets | [Feedback curves and attainment](05-teacher-alignment.md#a53) |
| RQ3: agreement with the independent human reference | [Partial-credit and binary comparisons](06-human-reference.md#a61) |
| RQ4: consistency between a rationale and its recorded score | [Instruments](04-methods.md#a44), [coverage and contradictions](06-human-reference.md#a62) |

## Find material cited by the article

The A numbers identify repository sections. Each linked section has a stable explicit anchor. Unprefixed section/table/figure numbers refer to the accompanying article, using the 16 October 2026 manuscript revision recorded in [provenance.json](provenance.json).

| Article destination | Repository entry | Contents |
|---|---|---|
| A.1 | [Predecessor results](01-predecessors.md) | ICWE protocol and ceiling-scoped results; related ICALT audit |
| A.2 | [Source and comparison details](02-source-comparisons.md) | Study-level evidence, comparison tables and inspected source versions |
| A.3 | [Additional design details](03-design.md) | Requirement rationale and output-contract validation |
| A.3.3 | [Detailed evaluation design](03-design.md#a33) | Full comparison-level plan behind the compact RQ roadmap |
| A.4.3 | [Independent human reference](04-methods.md#a43) | Coding scale, E5 adjudication, residual dissent and reference thresholds |
| A.4.4 | [Rationale instruments](04-methods.md#a44) | Score-blind instruments, judge configuration and diagnostics |
| A.4.5 | [Models, prompts and conditions](04-methods.md#a45) | All 51 arms, model identifiers, exact prompts and output contracts |
| A.4.6 | [Measurement and uncertainty](04-methods.md#a46) | Units, bootstrap protocols, missing outcomes and statistical status |
| A.5.1 | [Data availability](05-teacher-alignment.md#a51) | Available and missing cases by comparison |
| A.5.2.1 | [Replication gate](05-teacher-alignment.md#a521) | ICWE/gate differences and settings caveats |
| A.5.2.4 | [Serving substitution](05-teacher-alignment.md#a524) | Both P1 runs and provenance limitations |
| A.5.2.5 | [Component substitution](05-teacher-alignment.md#a525) | Jev, held-out routing and offline cascade |
| A.5.3 | [Feedback curves](05-teacher-alignment.md#a53) | Full-grid values, target attainment and coarse-grid limits |
| A.6 | [Human-reference and rationale results](06-human-reference.md) | Partial-credit sensitivity, binary and paired label comparisons, instrument coverage |
| A.7.3 | [Provenance gaps](07-provenance.md#a73) | Unrecovered original artifacts, unpinned identities and requirement coverage |

## Repository contents

| Path | What to use it for |
|---|---|
| `01-*.md` through `07-*.md` | Read the supplementary material directly |
| [tables/](tables/README.md) | Browse 15 tables or download their CSV representations |
| [figures/](figures/README.md) | Three diagrams as SVG, PDF and browser previews, aggregate inputs and rendering script |
| [prompts/](prompts/README.md) | Seven exact grading templates, shared rationale-judge prompt and enforced judge schema |
| [reproduction/](reproduction/README.md) | Pinned historical analysis/measurement source files and requirements for restricted-input reproduction |
| [references.md](references.md) | Bibliography, including distinct inspected and published source versions |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Aggregate fields, table conventions, units and missing-value meanings |
| [provenance.json](provenance.json) | File hashes and source identifiers for this material |
| [scripts/](scripts/README.md) | Validate links, hashes, section destinations and the data-free package |

## Reuse and reproduction

No TeX installation or appendix PDF is needed to read this repository.

Check the material without running analyses:

```bash
python3 scripts/validate.py
python3 scripts/check_aggregates.py
```

Redraw the existing figures from their aggregate values and already computed intervals:

```bash
python3 -m venv /tmp/jwe-appendix-venv
/tmp/jwe-appendix-venv/bin/python -m pip install -r figures/requirements.txt
/tmp/jwe-appendix-venv/bin/python figures/render.py --output-dir /tmp/jwe-appendix-figures
```

Python 3.10 or later is required for the repository checks. The pinned rendering environment was tested with Python 3.14.4. Rendering writes to the specified directory and leaves the archived assets intact. It does not estimate metrics or bootstrap new intervals. The historical analysis sources require the original restricted inputs, as described in [reproduction/README.md](reproduction/README.md); those analyses are separate from rendering the supplied aggregate figures.

The package contains no raw student answers, individual ratings or adjudication protocol. Results remain scoped to the article's nine-question course setting, with their stated operating points, denominators, uncertainty and exploratory status. See [scope and provenance](07-provenance.md) before interpreting comparisons.

## Version, citation and data access

This repository accompanies a manuscript prepared for the Journal of Web Engineering; it does not imply acceptance or publication. When referring to these materials, cite the authors and appendix title above, the repository URL, and the exact Git commit used. [provenance.json](provenance.json) records the manuscript revision, source snapshots and SHA-256 hashes; it is an integrity inventory, not a certification of the findings.

Student responses, individual ratings and adjudication records are not distributed. Aggregate checks and figure rendering are available from this repository; recomputing the study's estimates and confidence intervals requires authorized access to the restricted inputs. Data-access or methodological questions can be addressed to the corresponding author, Jonas Gwozdz, at jonas.gwozdz@htwk-leipzig.de. Access is not guaranteed. The included third-party style helper retains its own license; no broader reuse license is granted by that file.
