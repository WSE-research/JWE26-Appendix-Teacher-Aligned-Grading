# Online appendix: Teacher-Aligned Grading in Web-Based Assessment

Supplementary methods, comparison details, aggregate results, figures, prompts and reproduction code for the accompanying Journal of Web Engineering article by Jonas Gwozdz and Andreas Both.

## Find material cited by the article

The A numbers identify repository sections. Each linked section has a stable explicit anchor. Unprefixed section/table/figure numbers refer to the accompanying article, using its 15 October 2026 numbering.

| Article destination | Repository entry | Contents |
|---|---|---|
| A.1 | [Predecessor results](01-predecessors.md) | ICWE protocol and ceiling-scoped results; related ICALT audit |
| A.2 | [Source and comparison details](02-source-comparisons.md) | Study-level evidence, comparison tables and inspected source versions |
| A.3 | [Additional design details](03-design.md) | Requirement rationale and output-contract validation |
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
| A.7.3 | [Provenance gaps](07-provenance.md#a73) | Missing original scripts/outputs, unpinned identities and requirement coverage |

## Repository contents

| Path | What to use it for |
|---|---|
| `01-*.md` through `07-*.md` | Read the supplementary material directly |
| [tables/](tables/README.md) | Browse 13 tables or download their CSV representations |
| [figures/](figures/README.md) | Three diagrams as SVG, PDF and browser previews, aggregate inputs and rendering script |
| [prompts/](prompts/README.md) | Seven exact grading templates, shared rationale-judge prompt and enforced judge schema |
| [reproduction/](reproduction/README.md) | Pinned historical analysis/measurement source files and requirements for restricted-input reproduction |
| [references.md](references.md) | Bibliography, including distinct inspected and published source versions |
| [provenance.json](provenance.json) | File hashes and source identifiers for this material |
| [scripts/](scripts/README.md) | Validate links, hashes, section destinations and the data-free package |

## Reuse and reproduction

No TeX installation or appendix PDF is needed to read this repository.

Check the material without running analyses:

```bash
python3 scripts/validate.py
```

Redraw the existing figures from their aggregate values and already computed intervals:

```bash
python3 -m pip install -r figures/requirements.txt
python3 figures/render.py
```

This rendering step does not estimate metrics or bootstrap new intervals. The historical analysis sources require the original restricted inputs, as described in [reproduction/README.md](reproduction/README.md); those analyses are separate from rendering the supplied aggregate figures.

The package contains no raw student answers, individual ratings or adjudication protocol. Results remain scoped to the article's nine-question course setting, with their stated operating points, denominators, uncertainty and exploratory status. See [scope and provenance](07-provenance.md) before interpreting comparisons.
