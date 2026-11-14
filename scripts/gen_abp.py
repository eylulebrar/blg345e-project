#!/usr/bin/env python3
"""
Alternating Bit Protocol (ABP) - JSON model generator.

Models a sender (s_bit in {0, 1}), a receiver (r_bit in {0, 1}), and a
finite-state abstraction of an unreliable communication channel with a
timeout-retransmission loop. Mirrors models/abp.smv line by line and writes
all reachable states from the initial configuration to models/abp.json.

Usage:  python3 scripts/gen_abp.py
"""
import json
import os
from collections import deque

PROPS = ["packet_lost", "ack_received", "bit_error"]
CHANNELS = ["deliver", "lose", "corrupt"]

# State = (s_bit, r_bit, phase)
# phase in:
#   ready         - sender is ready to transmit packet with s_bit
#   data_sent     - data packet is in flight over the unreliable channel
#   pkt_lost      - channel dropped the data packet (packet_lost = True)
#   pkt_corrupted - channel corrupted the packet; receiver discarded it (bit_error = True)
#   ack_sent      - receiver accepted (or re-acknowledged) packet and sent ACK
#   ack_rcvd      - sender received valid ACK for its outstanding packet (ack_received = True)
#   timeout       - sender timed out after loss/corruption and will retransmit
INIT = (0, 0, "ready")


def step(state, channel):
    """Deterministic next state for a given state and channel outcome."""
    s_bit, r_bit, phase = state

    n_s = s_bit
    n_r = r_bit

    if phase == "ready":
        n_phase = "data_sent"
    elif phase == "data_sent":
        if channel == "deliver":
            n_phase = "ack_sent"
            if s_bit == r_bit:
                n_r = 1 - r_bit  # expected bit matched: accept & flip r_bit
        elif channel == "lose":
            n_phase = "pkt_lost"
        else:  # channel == "corrupt"
            n_phase = "pkt_corrupted"
    elif phase == "pkt_lost":
        n_phase = "timeout"
    elif phase == "pkt_corrupted":
        n_phase = "timeout"
    elif phase == "ack_sent":
        if channel == "deliver":
            n_phase = "ack_rcvd"
        else:  # ACK lost/corrupted -> sender times out
            n_phase = "timeout"
    elif phase == "ack_rcvd":
        n_phase = "ready"
        n_s = 1 - s_bit          # advance sender sequence bit for next packet
    elif phase == "timeout":
        n_phase = "data_sent"    # retransmit the unacknowledged packet
    else:
        n_phase = phase

    return (n_s, n_r, n_phase)


def successors(state):
    out = []
    for ch in CHANNELS:
        nxt = step(state, ch)
        if nxt not in out:
            out.append(nxt)
    return out


def state_id(state):
    s_bit, r_bit, phase = state
    return f"s{s_bit}_r{r_bit}_{phase}"


def labels(state):
    _, _, phase = state
    truth = {
        "packet_lost": phase == "pkt_lost",
        "ack_received": phase == "ack_rcvd",
        "bit_error": phase == "pkt_corrupted",
    }
    return [p for p in PROPS if truth[p]]


def main():
    visited = {INIT}
    queue = deque([INIT])
    order = []
    succ_map = {}

    while queue:
        s = queue.popleft()
        order.append(s)
        succs = successors(s)
        succ_map[s] = succs
        for nxt in succs:
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)

    states = {
        state_id(s): {
            "labels": labels(s),
            "transitions": [state_id(nxt) for nxt in succ_map[s]],
        }
        for s in order
    }

    model = {
        "atomic_propositions": PROPS,
        "initial_states": [state_id(INIT)],
        "states": states,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "models", "abp.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)
        f.write("\n")

    edge_count = sum(len(v["transitions"]) for v in states.values())
    print(f"Wrote {len(states)} states and {edge_count} transitions to {os.path.normpath(out_path)}")


if __name__ == "__main__":
    main()
