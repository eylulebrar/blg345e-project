"""philosophers.json dosyasını üretir.

SMV modelindeki kuralların aynısını Python'da uygular, başlangıç durumundan
BFS ile erişilebilen bütün durumları ve geçişleri bulup JSON'a yazar.

Durum = (p0, p1, p2), her biri "T" (Thinking), "L" (HoldingLeft) veya "E" (Eating).
Filozof i'nin sol çatalı i, sağ çatalı (i+1) mod 3'tür. Çatalların durumu ayrıca
tutulmaz, filozofların durumundan türetilir.
"""
import json
import os
from collections import deque

N = 3
PROPS = ["P0_eating", "P1_eating", "P2_eating", "deadlock"]
INITIAL = ("T", "T", "T")


def fork_free(state, f):
    return state[f] not in ("L", "E") and state[(f - 1) % N] != "E"


def step(state, i):
    """Filozof i'nin tek bir atomik adımından sonraki durumu döndürür.
    Adım atamıyorsa None döner."""
    s = list(state)
    if s[i] == "T" and fork_free(state, i):
        s[i] = "L"
    elif s[i] == "L" and fork_free(state, (i + 1) % N):
        s[i] = "E"
    elif s[i] == "E":
        s[i] = "T"
    else:
        return None
    return tuple(s)


def successors(state):
    targets = []
    for i in range(N):
        t = step(state, i)
        if t is not None and t not in targets:
            targets.append(t)
    if not targets:
        targets.append(state)
    return targets


def labels(state):
    truth = {
        "P0_eating": state[0] == "E",
        "P1_eating": state[1] == "E",
        "P2_eating": state[2] == "E",
        "deadlock": all(x == "L" for x in state),
    }
    return [p for p in PROPS if truth[p]]


def state_id(state):
    return "s_" + "".join(state)


def main():
    visited = {INITIAL}
    queue = deque([INITIAL])
    states = {}

    while queue:
        s = queue.popleft()
        targets = []
        for t in successors(s):
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

    out = os.path.join(os.path.dirname(__file__), "..", "models", "philosophers.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)
    print(f"Wrote {len(states)} states to {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
