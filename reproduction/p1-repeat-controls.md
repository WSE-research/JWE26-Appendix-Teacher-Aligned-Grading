# Historical P1 repeat-control evidence

[Analysis snapshots](README.md) · [Serving comparison](../05-teacher-alignment.md#a524)

The API repeat controls were run on 19 August 2026 after the first serving comparison. Preserved execution records contain launch commands, comparison code and successful console output. They are historical execution evidence, not a new reconstruction from available prediction files.

| Temperature | Run tags | Loaded rows per run | Common comparison keys | Discordant scores |
|---|---|---|---|---|
| 0.2 | `t02a`, `t02b` | 450 | 450 | 12 |
| 0 | `t00a`, `t00b` | 450 | 450 | 3 |

The recorded loader selects parseable predictions at 40 examples that match the historical pool. It keys records by question, student identifier, exact answer text and fold, then compares the stored binary scores on shared keys. No student-level data or identifiers are included here.

The launch record is dated 19 August 2026, 09:27:52 UTC; the successful comparison output is dated 09:36:54 UTC. The retained source records are lines 2168–2169 and 2186–2187 of the original execution log, whose SHA-256 is `7a1a529db116a559e1352ab97a06c4d6622b364c9bbc785ad07e53869b9889bf`. This summary was checked against the retained extract on 16 October 2026. The underlying private log and prediction CSVs are not distributed here; the CSVs have not been recovered, and the original source log hash does not make them available.

The same console output also contains a P1 summary line inserted as a literal string. That line is not evidence of a calculation of P1. The later reconstruction of both P1 comparisons is implemented in [31_jwe_n40_agreement.py](teacher-alignment/experiments/scripts/31_jwe_n40_agreement.py), using separate, pinned prediction files and the repository's significance routine.

These two repeat pairs establish the observed discordance at their recorded settings. They do not identify routing or batching as its cause, establish a general noise floor for other models, or demonstrate permanent loss of the missing CSVs.
