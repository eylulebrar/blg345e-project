"""Compares NuSMV's reachable-state list with the states of a JSON model.

Usage:
    python3 scripts/compare_nusmv.py <model_name> <nusmv_states.txt> <model.json>

<nusmv_states.txt> is the output of `print_reachable_states -v`.
Each NuSMV state (an assignment to the SMV state variables) is mapped to the
JSON state-ID naming scheme of that model, and the two sets are compared.
"""
import json
import re
import sys

PHIL = {"thinking": "T", "holding_left": "L", "eating": "E"}

# NuSMV variable assignment -> JSON state ID, one function per model.
ID_OF = {
    "philosophers": lambda v: "s_" + "".join(PHIL[v[f"p{i}"]] for i in range(3)),
    "peterson": lambda v: f"{v['pc0']}__{v['pc1']}__t{v['turn']}",
    "abp": lambda v: f"s{v['s_bit']}_r{v['r_bit']}_{v['phase']}",
    "railway": lambda v: f"{v['train']}__{v['gate']}__{v['ctrl']}",
    "elevator": lambda v: (f"{v['pos']}__{v['dir']}__{v['door']}__req_{v['req']}"
                           + ("__STALLED" if v["stalled"] == "TRUE" else "")),
}

HEADER = re.compile(r"^\s*-+\s*State\s+\d+\s*-*\s*$")
ASSIGN = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*=\s*(\S+)\s*$")


def parse_states(path):
    states, current = [], None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if HEADER.match(line):
                current = {}
                states.append(current)
            elif current is not None:
                m = ASSIGN.match(line)
                if m:
                    current[m.group(1)] = m.group(2)
    return states


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ID_OF:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    name, states_path, json_path = sys.argv[1:]

    nusmv = parse_states(states_path)
    if not nusmv:
        print(f"[{name}] could not find any '------- State n ------' blocks "
              f"in {states_path}", file=sys.stderr)
        sys.exit(1)
    nusmv_ids = {ID_OF[name](v) for v in nusmv}

    with open(json_path, encoding="utf-8") as f:
        json_ids = set(json.load(f)["states"])

    only_nusmv = sorted(nusmv_ids - json_ids)
    only_json = sorted(json_ids - nusmv_ids)
    print(f"[{name}] NuSMV reachable states: {len(nusmv_ids)}, "
          f"JSON states: {len(json_ids)}, common: {len(nusmv_ids & json_ids)}")
    if only_nusmv or only_json:
        print(f"[{name}] MISMATCH  only in NuSMV: {only_nusmv}  only in JSON: {only_json}")
        sys.exit(1)
    print(f"[{name}] state sets are identical")


if __name__ == "__main__":
    main()
