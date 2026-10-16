# Repository checks

[Appendix index](../README.md)

Both commands use Python 3.10 or later and the standard library. They run offline, require no credentials or restricted inputs, write no files, and exit with a nonzero status on a failed check. They can also be invoked by absolute path from another working directory. Run Python without `-O` for the integrity validator.

```bash
python3 scripts/validate.py
python3 scripts/check_aggregates.py
```

## Package integrity

`validate.py` checks the file inventory and SHA-256 hashes; local Markdown links and explicit anchors; required article destinations; CSV shape; cell equality between each CSV, its Markdown page and its chapter table; historical source-file pins; figure-input pins; the judge schema; and the absence of named restricted-data files or a monolithic PDF/TeX entry point.

This is an integrity check, not a comprehensive privacy detector or a test of the scientific conclusions. It does not open remote bibliography links. A file hash is only as trustworthy as the supplied manifest.

## Selected aggregate relationships

`check_aggregates.py` independently derives or compares:

- First and sustained target attainment in Table A.9 from all 14 trajectories in Table A.10.
- Gate differences in Table A.6, and base-arm percentages, Wilson intervals and subset counts in Table A.7.
- The two coders' binary agreement with the historical teacher label from Figure A.1's crosstabs, including the primary-threshold relation.
- Table A.11's primary binary estimates and intervals against Figure A.4's aggregate inputs, and Table A.12's primary paired point differences against those estimates.
- Contradiction and comparable-case totals from Table A.14.

The checker allows for the stated display rounding. It does not recompute bootstrap intervals, validate every prose claim, recover individual observations or check the stricter-threshold paired intervals. The checks are therefore narrower than a full reproduction of the analyses.

## Figure regeneration

[figures/render.py](../figures/render.py) redraws the supplied aggregate estimates into an explicitly selected directory outside this repository. See the [rendering instructions](../figures/README.md). The historical analysis entry points and their restricted-input requirements are documented in [reproduction/README.md](../reproduction/README.md).
