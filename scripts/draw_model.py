"""Bir veya birden fazla model JSON'unu state diyagramına çevirir.

Kullanım:
    python3 scripts/draw_model.py models/peterson.json
    python3 scripts/draw_model.py models/*.json

Çıktılar report/diagrams/<isim>.dot ve <isim>.png olarak kaydedilir.
"""
import json
import os
import shutil
import subprocess
import sys
from collections import deque

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "report", "diagrams")


def esc(text):
    """Graphviz için tırnak işaretlerini kaçırır."""
    return text.replace('"', '\\"')


def reachable(model):
    """Başlangıç durumlarından BFS ile erişilebilen durumlar."""
    states = model["states"]
    seen = set(s for s in model["initial_states"] if s in states)
    queue = deque(seen)
    while queue:
        s = queue.popleft()
        for t in states[s]["transitions"]:
            if t in states and t not in seen:
                seen.add(t)
                queue.append(t)
    return seen


def to_dot(model, title):
    states = model["states"]
    initial = model["initial_states"]
    reach = reachable(model)

    lines = [
        "digraph G {",
        "  rankdir=LR;",
        f'  label="{esc(title)}"; labelloc=t; fontsize=20; fontname="Helvetica";',
        '  node [shape=box, style=rounded, fontname="Helvetica", fontsize=11];',
        '  edge [arrowsize=0.7];',
    ]

    # Başlangıç durumlarına boşluktan gelen ok
    for i, s in enumerate(initial):
        lines.append(f'  __start{i} [shape=point, width=0.08];')
        lines.append(f'  __start{i} -> "{esc(s)}";')

    # Düğümler: üst satırda kimlik, alt satırda etiketler
    for sid, st in states.items():
        props = ", ".join(st["labels"]) if st["labels"] else "∅"
        attrs = [f'label="{esc(sid)}\\n{{{esc(props)}}}"']
        if sid in initial:
            attrs.append("penwidth=2")
        if sid not in reach:
            attrs.append('style="rounded,dashed", color=gray55, fontcolor=gray55')
        lines.append(f'  "{esc(sid)}" [{", ".join(attrs)}];')

    # Kenarlar
    for sid, st in states.items():
        for t in st["transitions"]:
            lines.append(f'  "{esc(sid)}" -> "{esc(t)}";')

    lines.append("}")
    return "\n".join(lines)


def draw(path):
    with open(path, encoding="utf-8") as f:
        model = json.load(f)

    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(OUT_DIR, exist_ok=True)
    dot_path = os.path.join(OUT_DIR, f"{name}.dot")
    png_path = os.path.join(OUT_DIR, f"{name}.png")

    with open(dot_path, "w", encoding="utf-8") as f:
        f.write(to_dot(model, name))

    if shutil.which("dot") is None:
        print(f"Wrote {os.path.normpath(dot_path)} (Graphviz not found, PNG skipped)")
        return
    subprocess.run(["dot", "-Tpng", "-Gdpi=150", dot_path, "-o", png_path], check=True)
    print(f"Wrote {os.path.normpath(png_path)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/draw_model.py <model.json> [...]", file=sys.stderr)
        sys.exit(2)
    for path in sys.argv[1:]:
        draw(path)


if __name__ == "__main__":
    main()