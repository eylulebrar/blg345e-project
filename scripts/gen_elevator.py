#!/usr/bin/env python3
"""
Three-Floor Elevator Controller - JSON model generator.

State = (pos, dir, door, req, stalled). One transition = one controller
step. The step function below mirrors the case-blocks of
models/elevator.smv line by line, so both files describe the same system.
Only states reachable from the initial state are written to
models/elevator.json.

Usage:  python3 scripts/gen_elevator.py
"""
import json
import os
from collections import deque

POS = ["F1", "F1_2", "F2", "F2_3", "F3"]       # floors + intermediate positions
FLOORS = ["F1", "F2", "F3"]
DIRS = ["Up", "Down", "Stationary"]
DOORS = ["Closed", "Opening", "Open", "Closing"]
REQS = ["none", "F1", "F2", "F3"]

INIT = ("F1", "Stationary", "Closed", "none", False)
PROPS = ["moving", "doors_open", "stalled"]

# Inputs chosen by the environment in every step (IVAR in NuSMV).
CALLS = ["none", "F1", "F2", "F3"]              # new floor request
EMERGENCY = [False, True]                       # emergency-stop button


def at_floor(pos):
    return pos in FLOORS


def req_above(pos, req):
    return POS.index(pos) < POS.index(req) if req != "none" else False


def req_below(pos, req):
    return POS.index(pos) > POS.index(req) if req != "none" else False


def step(s, call, emergency):
    """Deterministic next state for one choice of the inputs."""
    pos, dr, door, req, stalled = s
    moving = dr != "Stationary"
    idle = not stalled and dr == "Stationary" and door == "Closed" and req == "none"
    stall_now = moving and not at_floor(pos) and emergency

    # next(stalled): terminal once entered
    if stalled or stall_now:
        n_stalled = True
    else:
        n_stalled = False

    # next(dir)
    if stalled or stall_now:
        n_dir = "Stationary"
    elif dr == "Stationary" and door == "Closed" and req_above(pos, req):
        n_dir = "Up"
    elif dr == "Stationary" and door == "Closed" and req_below(pos, req):
        n_dir = "Down"
    elif moving and pos == req:
        n_dir = "Stationary"                      # arrived: stop
    else:
        n_dir = dr

    # next(pos): one position per step, only while moving
    if stall_now:
        n_pos = pos
    elif dr == "Up" and pos != req:
        n_pos = POS[POS.index(pos) + 1]
    elif dr == "Down" and pos != req:
        n_pos = POS[POS.index(pos) - 1]
    else:
        n_pos = pos

    # next(door): opens only at the requested floor while stationary
    if not stalled and dr == "Stationary" and at_floor(pos) and door == "Closed" and pos == req:
        n_door = "Opening"
    elif door == "Opening":
        n_door = "Open"
    elif door == "Open":
        n_door = "Closing"
    elif door == "Closing":
        n_door = "Closed"
    else:
        n_door = door

    # next(req): accepted only when idle, cleared when the doors close
    if idle:
        n_req = call
    elif door == "Closing":
        n_req = "none"
    else:
        n_req = req

    return (n_pos, n_dir, n_door, n_req, n_stalled)


def successors(s):
    out = []
    for call in CALLS:
        for emergency in EMERGENCY:
            n = step(s, call, emergency)
            if n not in out:
                out.append(n)
    return out


def sid(s):
    pos, dr, door, req, stalled = s
    name = "__".join([pos, dr, door, "req_" + req])
    return name + "__STALLED" if stalled else name


def labels(s):
    _, dr, door, _, stalled = s
    out = []
    if dr != "Stationary":
        out.append("moving")
    if door == "Open":
        out.append("doors_open")
    if stalled:
        out.append("stalled")
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
        states[sid(s)] = {"labels": labels(s),
                          "transitions": [sid(n) for n in successors(s)]}

    return {
        "atomic_propositions": PROPS,
        "initial_states": [sid(INIT)],
        "states": states,
    }


if __name__ == "__main__":
    model = build()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "models", "elevator.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)

    st = model["states"].values()
    n_edges = sum(len(v["transitions"]) for v in st)
    n_stalled = sum("stalled" in v["labels"] for v in st)
    n_bad = sum({"moving", "doors_open"} <= set(v["labels"]) for v in st)
    print(f"Wrote {out}")
    print(f"States: {len(model['states'])}  Transitions: {n_edges}  "
          f"Stalled states: {n_stalled}  moving&doors_open states: {n_bad}")
