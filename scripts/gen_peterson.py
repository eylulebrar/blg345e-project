"""peterson.json dosyasını üretir.

SMV modelindeki kuralların aynısını Python'da uygular, başlangıç durumundan
BFS ile erişilebilen bütün durumları ve geçişleri bulup JSON'a yazar.
"""
import json
import os
from collections import deque

PROPS = ["P0_in_CS", "P1_in_CS", "flag0", "flag1", "turn_is_1"]
INITIAL = ("idle", "idle", 0)          # (pc0, pc1, turn)


def flag(pc):
    """Bayrak, süreç idle değilken kalkıktır."""
    return pc != "idle"


def step(state, i):
    """Süreç i'nin tek bir atomik adımından sonraki durumu döndürür."""
    pcs = list(state[:2])
    turn = state[2]
    j = 1 - i

    if pcs[i] == "idle":                       # flag[i] = true
        pcs[i] = "flag_set"
    elif pcs[i] == "flag_set":                 # turn = j
        pcs[i] = "waiting"
        turn = j
    elif pcs[i] == "waiting":                  # while flag[j] and turn == j: wait
        if not (flag(pcs[j]) and turn == j):
            pcs[i] = "critical"
    elif pcs[i] == "critical":                 # flag[i] = false
        pcs[i] = "idle"

    return (pcs[0], pcs[1], turn)


def labels(state):
    pc0, pc1, turn = state
    truth = {
        "P0_in_CS": pc0 == "critical",
        "P1_in_CS": pc1 == "critical",
        "flag0": flag(pc0),
        "flag1": flag(pc1),
        "turn_is_1": turn == 1,
    }
    return [p for p in PROPS if truth[p]]


def state_id(state):
    pc0, pc1, turn = state
    return f"{pc0}__{pc1}__t{turn}"


def main():
    visited = {INITIAL}
    queue = deque([INITIAL])
    states = {}

    while queue:
        s = queue.popleft()
        targets = []
        for i in (0, 1):                       # interleaving: P0 veya P1 hareket eder
            t = step(s, i)
            if state_id(t) not in targets:     # aynı hedefi iki kez yazma
                targets.append(state_id(t))
            if t not in visited:
                visited.add(t)
                queue.append(t)
        states[state_id(s)] = {"labels": labels(s), "transitions": targets}

    model = {
        "atomic_propositions": PROPS,
        "initial_states": [state_id(INITIAL)],
        "states": states,
    }

    out = os.path.join(os.path.dirname(__file__), "..", "models", "peterson.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)
    print(f"Wrote {len(states)} states to {os.path.normpath(out)}")


if __name__ == "__main__":
    main()