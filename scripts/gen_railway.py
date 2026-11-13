#!/usr/bin/env python3
"""
Railway Crossing Controller - JSON model generator.

Builds the synchronous product of three component machines
(Train x Gate x Controller), keeps only states reachable from the
initial state, and writes models/railway.json.

Usage:  python3 scripts/gen_railway.py
"""
import json
import os
from collections import deque
from itertools import product

TRAIN = ["Far", "Approaching", "InCrossing", "Passed"]
GATE = ["Open", "Lowering", "Closed", "Raising"]
CTRL = ["Idle", "ClosingRequested", "OpeningRequested"]

INIT = ("Far", "Open", "Idle")
PROPS = ["train_in_crossing", "gate_is_down", "unsafe_state"]


# ---- local next-state functions (read the CURRENT global state) ----------
# Each returns the set of allowed next local states (synchronous semantics).

def next_train(t, g, c):
    # Train moves on its own: it may stay or advance one step.
    # It may enter InCrossing regardless of the gate (fast-train scenario).
    return {
        "Far": ["Far", "Approaching"],
        "Approaching": ["Approaching", "InCrossing"],
        "InCrossing": ["InCrossing", "Passed"],
        "Passed": ["Passed", "Far"],
    }[t]


def next_ctrl(t, g, c):
    # Controller reacts deterministically to what it observes.
    if c == "Idle" and t in ("Approaching", "InCrossing"):
        return ["ClosingRequested"]
    if c == "ClosingRequested" and t == "Passed":
        return ["OpeningRequested"]
    if c == "OpeningRequested" and g == "Open":
        return ["Idle"]
    return [c]


def next_gate(t, g, c):
    if g == "Open" and c == "ClosingRequested":
        return ["Lowering"]
    if g == "Lowering":
        return ["Lowering", "Closed"]      # at least one step in Lowering
    if g == "Closed" and c == "OpeningRequested":
        return ["Raising"]
    if g == "Raising":
        return ["Raising", "Open"]
    return [g]


def successors(s):
    t, g, c = s
    return [(nt, ng, nc)
            for nt, ng, nc in product(next_train(t, g, c),
                                      next_gate(t, g, c),
                                      next_ctrl(t, g, c))]


def sid(s):
    return "__".join(s)


def labels(s):
    t, g, _ = s
    out = []
    if t == "InCrossing":
        out.append("train_in_crossing")
    if g == "Closed":
        out.append("gate_is_down")
    if t == "InCrossing" and g != "Closed":
        out.append("unsafe_state")
    return out


def build():
    seen = {INIT}
    order = [INIT]
    q = deque([INIT])
    while q:
        s = q.popleft()
        for n in successors(s):
            if n not in seen:
                seen.add(n)
                order.append(n)
                q.append(n)

    states = {}
    for s in order:
        targets = []
        for n in successors(s):
            if sid(n) not in targets:
                targets.append(sid(n))
        states[sid(s)] = {"labels": labels(s), "transitions": targets}

    return {
        "atomic_propositions": PROPS,
        "initial_states": [sid(INIT)],
        "states": states,
    }


if __name__ == "__main__":
    model = build()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "models", "railway.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)

    n_states = len(model["states"])
    n_edges = sum(len(v["transitions"]) for v in model["states"].values())
    n_unsafe = sum("unsafe_state" in v["labels"] for v in model["states"].values())
    print(f"Wrote {out}")
    print(f"States: {n_states}  Transitions: {n_edges}  Unsafe states: {n_unsafe}")
