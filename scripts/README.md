# Repository checks

Run `python3 scripts/validate.py` from the appendix root, or pass the script's absolute path from any directory. It checks file hashes, local links/anchors, required A destinations, CSV shape, prompt/schema integrity and the absence of a monolithic appendix PDF or TeX publication entry point. It uses Python's standard library and does not call APIs, estimate metrics, access private inputs or alter the package.

To redraw the supplied diagrams, use [figures/render.py](../figures/render.py). Historical analysis entry points and their restricted-input requirements are documented in [reproduction/README.md](../reproduction/README.md).

[Appendix index](../README.md)
