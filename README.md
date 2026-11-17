# BLG 345E – Term Project Phase 1

Explicit-state Kripke structure parser and reachability checker, plus five
system models in JSON and NuSMV format.

## Requirements
- Python 3 (standard library only)
- NuSMV 2.6.0 or newer (only for the oracle comparison)
- Graphviz `dot` (only for diagrams)

## Usage
```sh
./my_checker --parse models/railway.json
```
Successful runs print the five metric lines to stdout and exit with 0.
Validation errors are printed to stderr with a `[SYNTAX ERROR]`,
`[SCHEMA ERROR]` or `[SEMANTIC ERROR]` prefix and exit with 1.

## Layout
| Path | Content |
|---|---|
| `my_checker` | executable entry point (runs `src/checker.py`) |
| `src/checker.py` | parser, validation, graph structure, BFS |
| `models/` | `philosophers`, `peterson`, `abp`, `railway`, `elevator` (`.json` + `.smv`) |
| `scripts/gen_<system>.py` | regenerate `models/<system>.json` |
| `scripts/run_all.sh` | run my_checker and NuSMV on everything, save outputs to `report/outputs/` |
| `scripts/compare_nusmv.py` | compare NuSMV's reachable states with a JSON model |
| `scripts/draw_model.py`, `scripts/report_figures.py` | state diagrams |
| `tests/` | light-switch example and invalid test models |
| `report/` | LaTeX report (`report.tex`) and its figures/outputs |

## Reproducing the report outputs
```sh
sh scripts/run_all.sh
cd report && latexmk -pdf report.tex
```
