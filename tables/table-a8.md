# Table A.8: Exploratory Jev component substitution

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

[CSV](table-a8.csv) · [Context](../05-teacher-alignment.md#table-a8)
