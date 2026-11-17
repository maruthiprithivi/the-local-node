"""Load MANIFEST.csv and parse every session."""
from __future__ import annotations

import csv
import os

from .parsers import PARSERS

MAIN_FMTS = {"qwen-chat-jsonl", "omp-jsonl", "dsh-agent-log", "dsh-session-v4", "requests-jsonl", "t2-openshell-json"}


def harness_group(h: str) -> str:
    if h.startswith("qwen-p"):
        return "qwen (prompt-trim variants)"
    if h.startswith("qwen-review"):
        return "qwen (review-loop variants)"
    if h in ("pi", "pi-solpi"):
        return "pi / SoL-Pi"
    return h


def model_group(m: str) -> str:
    return {"deepseek-v4-flash-0731": "deepseek-v4-flash",
            "qwen3.8-27b-q4km-bimatrix-rebuild": "qwen3.8-27b-q4km-rebuild",
            "thinklite-27b-q4km": "thinklite-27b"}.get(m, m)


def task_group(t: str, run_set: str) -> str:
    if t in ("everyday", "phaseA-everyday"):
        return "everyday"
    return t


def iter_sessions(log_dir: str):
    with open(os.path.join(log_dir, "MANIFEST.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    # The packer wrote 17 dsh-superagent runs' main and subagent sessions to the same
    # dest_path, so MANIFEST lists 17 files twice. Count each file once, and add the
    # overwritten sessions recovered by replay/recover.py when ../recovered exists.
    seen, uniq = set(), []
    for r in rows:
        if r["dest_path"] in seen:
            continue
        seen.add(r["dest_path"])
        uniq.append(r)
    rows = uniq
    rec = os.path.join(os.path.dirname(os.path.abspath(log_dir)), "recovered", "RECOVERED.csv")
    if os.path.exists(rec):
        with open(rec, newline="") as f:
            rows += list(csv.DictReader(f))
    root = os.path.dirname(os.path.abspath(log_dir))
    for r in rows:
        r["_path"] = os.path.join(root, r["dest_path"])
        r["_scope"] = ("excluded:computer-use" if r["computer_use"] == "True" else
                       "excluded:research-agent" if r["fmt"] == "research-agent-json" else
                       "aider" if r["fmt"] == "aider-chat-history" else
                       "main" if r["fmt"] in MAIN_FMTS else "excluded:unknown-format")
        r["_sess"] = PARSERS[r["fmt"]](r["_path"]) if r["fmt"] in PARSERS else None
        yield r
