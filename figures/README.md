# Figures and data-free rendering

| Appendix figure | Preview / vector asset | Data and context |
|---|---|---|
| A.1: teacher-label relation | [SVG](fig08_teacher_label_relation.svg), [PDF](fig08_teacher_label_relation.pdf), [PNG](fig08_teacher_label_relation.png) | [Aggregate crosstab](data/teacher_label_crosstab.csv); [caption and method](../04-methods.md#figure-a1) |
| A.3: partial-credit model/reference agreement | [SVG](fig10_model_vs_reference.svg), [PDF](fig10_model_vs_reference.pdf), [PNG](fig10_model_vs_reference.png) | [Aggregate estimates](data/consensus_model_vs_reference.json); [caption and results](../06-human-reference.md#figure-a3) |
| A.4: binary model/reference and teacher-label agreement | [SVG](fig11_binary_runs_vs_reference.svg), [PDF](fig11_binary_runs_vs_reference.pdf), [PNG](fig11_binary_runs_vs_reference.png) | [Aggregate estimates](data/binary_runs_vs_reference.json); [caption and results](../06-human-reference.md#figure-a4) |

Figure A.2 identifies the textual [prompt templates and output contracts](../prompts/README.md), rather than an additional diagram.

Run `python3 figures/render.py` from the appendix root or invoke the script by absolute path from any working directory. Install [requirements.txt](requirements.txt) beforehand. The script loads only the three aggregate input files, draws existing points/counts/intervals and writes SVG/PDF/PNG and typography/layout audits. It never reads student responses or computes new model metrics or bootstrap intervals. The plot functions retain the previously measured JWE width, 335.7426 TeX pt. See [provenance.json](provenance.json) for the original figure-script and input hashes and the limited derivation.

The shared style helper is included with its [MIT license](LICENSE-openresearch-cli.txt). Figure data and analysis provenance are described in the linked methods/results pages.

[Appendix index](../README.md)
