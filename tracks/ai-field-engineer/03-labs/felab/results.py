"""
felab.results — every lesson appends its numbers to results/<lesson>.csv.

Why bother: the capstone (lesson 15) is a sizing memo built from YOUR measurements.
If every run lands in a CSV with the target and model next to it, the memo
writes itself and you can quote real numbers when explaining the result.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from .targets import REPO_ROOT

RESULTS = REPO_ROOT / "results"


def record(lesson: str, row: dict) -> Path:
    """Append one row (dict) to results/<lesson>.csv, adding a timestamp."""
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{lesson}.csv"
    row = {"when": dt.datetime.now().isoformat(timespec="seconds"), **row}
    new = not path.exists()
    # If columns changed since the file was created, start a fresh file rather than corrupting it.
    if not new:
        with path.open() as f:
            header = next(csv.reader(f), [])
        if header != list(row):
            path = path.with_name(f"{path.stem}-{dt.datetime.now():%H%M%S}.csv")
            new = True
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    return path


def table(rows: list[dict], cols: list[str] | None = None) -> str:
    """Render rows as a fixed-width text table for the terminal."""
    if not rows:
        return "(no rows)"
    cols = cols or list(rows[0])
    fmt = lambda v: (f"{v:.3f}" if 0 < abs(v) < 1 else f"{v:,.1f}") if isinstance(v, float) else str(v)
    widths = {c: max(len(c), *(len(fmt(r.get(c, ""))) for r in rows)) for c in cols}
    line = "  ".join(c.ljust(widths[c]) for c in cols)
    out = [line, "  ".join("-" * widths[c] for c in cols)]
    for r in rows:
        out.append("  ".join(fmt(r.get(c, "")).rjust(widths[c]) for c in cols))
    return "\n".join(out)
