# Kripke Structure Checker – BLG 345E Term Project, Phase 1

An explicit-state Kripke structure parser and reachability checker, written as
the first phase of an LTL model checker for the *Logic and Computability*
course (BLG 345E) at Istanbul Technical University, Fall 2026.

Each of five classic systems is modeled twice: as an explicit JSON Kripke
structure and as an independently written NuSMV model. Our tool
`my_checker` validates the JSON model, builds its state graph and computes the
reachable states. NuSMV is then used as an oracle to check that both models
describe the same system.

![Railway crossing state diagram](report/diagrams/railway.png)

## Contents

- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [The five models](#the-five-models)
- [How the checker works](#how-the-checker-works)
- [Validation against NuSMV](#validation-against-nusmv)
- [Testing](#testing)
- [Repository layout](#repository-layout)
- [Report](#report)
- [Team](#team)
- [License](#license)

## What it does

A Kripke structure M = (S, S₀, R, L) is given as JSON:

```json
{
  "atomic_propositions": ["is_lit"],
  "initial_states": ["s_off"],
  "states": {
    "s_off": { "labels": [],         "transitions": ["s_on", "s_off"] },
    "s_on":  { "labels": ["is_lit"], "transitions": ["s_off", "s_on"] }
  }
}
```

`my_checker` reads such a file and

1. checks that it is valid JSON and follows the schema exactly,
2. builds an in-memory graph with one node object per state,
3. checks six semantic rules (no dangling transitions, no undeclared labels,
   every state has an outgoing transition, valid initial states, no duplicate
   declarations, at least one state),
4. runs a breadth-first search from the initial states and reports how many
   states are reachable and how many are not.

## Quick start

Requirements: Python 3 (standard library only). NuSMV 2.6+ is needed only for
the oracle comparison, Graphviz only for drawing diagrams.

```sh
git clone https://github.com/eylulebrar/blg345e-project.git
cd blg345e-project
./my_checker --parse models/railway.json
```

```
[PARSER]: Loaded models/railway.json successfully.
[METRICS]: Total declared states: 29
[METRICS]: Total transitions found: 80
[REACHABILITY]: Reachable states from initial node(s): 29
[DIAGNOSTICS]: Unreachable states detected: 0
```

On success the five lines above go to standard output and the program exits
with 0. Invalid models produce one message on standard error, starting with
`[SYNTAX ERROR]`, `[SCHEMA ERROR]` or `[SEMANTIC ERROR]`, and exit with 1.
Wrong usage exits with 2.

```sh
$ ./my_checker --parse tests/test1_dangling.json
[SEMANTIC ERROR]: State 's_on' references undeclared state 's_ghost'.
```

## The five models

| System | Semantics | State variables | Reachable / all combinations | Transitions |
|---|---|---|---|---|
| Dining Philosophers (3 philosophers, 3 forks) | interleaving | `p0, p1, p2` | 14 / 27 | 28 |
| Peterson's mutual exclusion (2 processes) | interleaving | `pc0, pc1, turn` | 20 / 32 | 40 |
| Alternating Bit Protocol | nondeterministic channel | `s_bit, r_bit, phase` | 22 / 28 | 32 |
| Railway crossing controller | synchronous product | `train, gate, ctrl` | 29 / 48 | 80 |
| Three-floor elevator controller | controller steps | `pos, dir, door, req, stalled` | 43 / 480 | 58 |

Some things the models show:

- **Dining Philosophers** reaches a deadlock when every philosopher holds the
  left fork (`s_LLL`). It is labeled `deadlock` and has a self-loop.
- **Peterson** never has both processes in the critical section; NuSMV proves
  `G !(P0_in_CS & P1_in_CS)`.
- **Alternating Bit Protocol** routes lost and corrupted packets into a timeout
  loop that retransmits the same packet, and never accepts a duplicate.
- **Railway crossing** is *not* safe: a fast train can enter the crossing while
  the gate is still open. NuSMV finds this as a two-step counterexample.
- **Elevator** never moves with open doors, and an emergency stop between
  floors leads to a terminal stalled state.

Every modeling decision and assumption is explained in the report.

## How the checker works

The implementation is in [`src/checker.py`](src/checker.py) and uses only
`json`, `sys` and `collections`. No graph library is used.

- **Parsing.** `load_json` parses the file and records duplicate keys through
  an `object_pairs_hook`, because Python's JSON parser would otherwise silently
  keep only the last one.
- **Schema.** `validate_schema` requires exactly the keys of the common schema
  and checks every field type.
- **Graph.** Every state becomes a `Node` with an id, a set of labels and an
  ordered list of references to its successor `Node` objects. The nodes are
  stored in an adjacency list (`KripkeGraph`). Edges are linked only after
  validation, so every reference points to an existing node.
- **Semantics.** `validate_semantics` checks the six rules; the first violation
  stops the program.
- **Reachability.** `reachable_states` is a breadth-first search from the
  initial states, O(|S| + |R|).

## Validation against NuSMV

The JSON models are produced by generator scripts (`scripts/gen_<system>.py`)
that encode the rules of each system and explore it by BFS. The `.smv` models
were written separately by hand. For every system:

- NuSMV and `my_checker` report the same number of reachable states;
- [`scripts/compare_nusmv.py`](scripts/compare_nusmv.py) reads NuSMV's full
  list of reachable states (`print_reachable_states -v`) and confirms that it
  is identical to the set of states in the JSON model;
- the SMV models contain invariants and LTL properties (mutual exclusion,
  deadlock persistence, door safety, …) that NuSMV checks.

To reproduce all outputs (requires NuSMV on the `PATH`):

```sh
sh scripts/run_all.sh
```

The outputs are written to [`report/outputs/`](report/outputs).

## Testing

[`tests/`](tests) contains the light-switch example and one invalid model for
every syntax, schema and semantic rule, including the five test cases required
by the assignment:

| Test | Expected result |
|---|---|
| `test1_dangling.json` | `[SEMANTIC ERROR]` – transition to an undeclared state |
| `test2_bad_label.json` | `[SEMANTIC ERROR]` – undeclared atomic proposition |
| `test3_no_transitions.json` | `[SEMANTIC ERROR]` – state without outgoing transitions |
| `test4_bad_initial.json` | `[SEMANTIC ERROR]` – undeclared initial state |
| `test5_unreachable.json` | valid, 1 unreachable state |

Further tests cover empty models, empty initial states, duplicate propositions,
labels, transitions and state keys, invalid JSON and schema violations.

## Repository layout

```
my_checker                 executable entry point (runs src/checker.py)
src/checker.py             parser, validation, graph structure, BFS
models/                    <system>.json and <system>.smv for the five systems
tests/                     light-switch example and invalid test models
scripts/
  gen_<system>.py          generate models/<system>.json
  run_all.sh               run my_checker and NuSMV on everything
  compare_nusmv.py         compare NuSMV's reachable states with a JSON model
  draw_model.py            draw a JSON model as a state diagram (Graphviz)
  report_figures.py        diagrams for the report (PDF)
report/
  report.tex, report.pdf   project report
  diagrams/                state diagrams (PNG)
  outputs/                 recorded console outputs
```

To draw a model:

```sh
python3 scripts/draw_model.py models/peterson.json
```

## Report

The full report is in [`report/report.pdf`](report/report.pdf). It covers the
modeling methodology, the state spaces and diagrams of all five systems, the
implementation, the test results and the comparison with NuSMV.

## Team

| Member | Main contribution |
|---|---|
| Eylül Ebrar Gülbeyaz | `my_checker`, test suite, Peterson model, tooling, report |
| Emirhan Ulu | Dining Philosophers model |
| Turgut Emre Sürenkök | Alternating Bit Protocol model |
| Eren Süslü | Railway Crossing Controller model |
| Oğuz Ünlüoğlu | Three-Floor Elevator Controller model |

Course: BLG 345E Logic and Computability, Istanbul Technical University.
Instructor: Asst. Prof. Mehmet Tahir Sandıkkaya.

## License

Released under the [MIT License](LICENSE). NuSMV is a separate project and is
not included in this repository.
