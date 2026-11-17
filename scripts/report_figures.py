"""Renders the five model diagrams for the LaTeX report as vector PDFs.

Uses exactly the same Graphviz drawing as scripts/draw_model.py (same layout,
title and node style), but writes PDF instead of PNG so the figures stay sharp
when zoomed in the report.

Usage:  python3 scripts/report_figures.py      (requires Graphviz `dot`)
Output: report/figures/<model>.pdf
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draw_model import to_dot  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "report", "figures")
MODELS = ["philosophers", "peterson", "abp", "railway", "elevator"]


def main():
    os.makedirs(OUT, exist_ok=True)
    for name in MODELS:
        with open(os.path.join(ROOT, "models", f"{name}.json"), encoding="utf-8") as f:
            model = json.load(f)
        pdf = os.path.join(OUT, f"{name}.pdf")
        subprocess.run(["dot", "-Tpdf", "-o", pdf], input=to_dot(model, name),
                       text=True, check=True)
        print(f"Wrote {os.path.relpath(pdf, ROOT)}")


if __name__ == "__main__":
    main()
