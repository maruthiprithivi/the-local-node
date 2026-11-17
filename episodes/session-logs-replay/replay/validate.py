#!/usr/bin/env python3
"""Draw the seeded validation sample and write a reading sheet.

    python -m replay.validate --logs ../logs [--n 30] [--seed 23]

Writes out/validation_sheet.md (one compact, readable digest per sampled
session, built straight from the raw transcript) and out/validation_sample.json.
Truth is recorded by the reader in validation.csv; `--score` refreshes the flag and
verdict columns from the latest run and computes precision from them.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from replay.detect import is_code_edit, is_test_step, step_failed, test_result  # noqa: E402
from replay.load import iter_sessions  # noqa: E402

FLAGS = ("hidden_error", "hidden_retry", "unrun_test")


def digest(sess):
    out = []
    for s in sess["steps"]:
        tag = []
        if is_code_edit(s):
            tag.append("EDIT")
        if is_test_step(s):
            tag.append("TEST:" + test_result(s))
        f, why = step_failed(s)
        if f:
            tag.append("FAIL:" + why)
        if s["kind"] == "shell":
            body = (s["cmd"] or "")[:220].replace("\n", " | ")
            tail = (s["output"] or "")[-260:].replace("\n", " | ")
            out.append(f'[{s["i"]}] {s["tool"]} exit={s["exit"]}({s["exit_src"]}) {" ".join(tag)}\n    $ {body}\n    > {tail}')
        else:
            out.append(f'[{s["i"]}] {s["tool"]} {" ".join(s["paths"])[:120]} {" ".join(tag)}'
                       + (" TOOL_ERROR: " + (s["output"] or "")[:160].replace("\n", " ") if s["tool_error"] else ""))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=os.path.join(HERE, "..", "logs"))
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.score:
        return score()
    rows = [json.loads(l) for l in open(os.path.join(HERE, "out", "sessions.jsonl"))]
    rows = [r for r in rows if "any_flag" in r and r.get("claim") == "claim"]
    flagged = sorted([r for r in rows if r["any_flag"]], key=lambda r: r["sid"])
    unflagged = sorted([r for r in rows if not r["any_flag"]], key=lambda r: r["sid"])
    rng = random.Random(a.seed)
    # stratify flagged so every flag type is checked at least 10 times when available
    pick = []
    for fl in FLAGS:
        pool = [r for r in flagged if r[fl] and r not in pick]
        pick += rng.sample(pool, min(10, len(pool)))
    rest = [r for r in flagged if r not in pick]
    if len(pick) < a.n:
        pick += rng.sample(rest, min(a.n - len(pick), len(rest)))
    un = rng.sample(unflagged, min(a.n, len(unflagged)))
    # sessions whose unresolved failure the local model cleared (EXPECTED / CHECK_FIXED / INCIDENTAL):
    # checked by hand so the hidden-error count does not rest on the model alone
    cleared = sorted([r for r in rows if r["error_judgments"] and not r["hidden_error"]], key=lambda r: r["sid"])
    cl = rng.sample(cleared, min(15, len(cleared)))
    # sessions with a retry the regex or the model called disclosed: checks the disclosure call itself
    disc = sorted([r for r in rows if r["retry_chains"] and not r["hidden_retry"]], key=lambda r: r["sid"])
    dc = rng.sample([r for r in disc if r not in cl], min(10, len(disc)))
    sample = ([("flagged", r) for r in pick] + [("unflagged", r) for r in un] + [("model_cleared", r) for r in cl]
              + [("retry_disclosed", r) for r in dc])
    want = {r["sid"]: (g, r) for g, r in sample}
    sheet = []
    for s in iter_sessions(a.logs):
        if s["session_id"] in want and s["_sess"]:
            g, r = want[s["session_id"]]
            flags = [f for f in FLAGS if r.get(f)]
            sheet.append((s["session_id"], f'## {g} | {s["session_id"]} | flags={flags} | task={r["task"]}\n'
                          f'source: {s["_path"]}\n'
                          f'unresolved={r["unresolved"]} judgments={r["error_judgments"]}\n'
                          f'retry_chains={r["retry_chains"]}\n'
                          f'test_claim={r["test_claim"]} last_edit={r["last_edit"]}\n\n'
                          f'{digest(s["_sess"])}\n\nFINAL:\n{s["_sess"]["final"]}\n'))
    order = {sid: n for n, (g, r) in enumerate(sample) for sid in [r["sid"]]}
    sheet.sort(key=lambda x: order[x[0]])
    with open(os.path.join(HERE, "out", "validation_sheet.md"), "w") as f:
        f.write("\n\n".join(t for _, t in sheet))
    with open(os.path.join(HERE, "out", "validation_sample.json"), "w") as f:
        json.dump([{"group": g, "sid": r["sid"], "flags": [x for x in FLAGS if r.get(x)]} for g, r in sample], f, indent=1)
    print(len(pick), "flagged,", len(un), "unflagged,", len(cl), "model-cleared error candidates,", len(dc), "retry-disclosed")


def _refresh(rows):
    """Re-derive the run-dependent columns of validation.csv from the latest run (out/sessions.jsonl).

    The reader's truth per flag ({flag}_truth), the notes and flags_first_pass are never touched.
    Verdicts are a pure function of truth and the current flag: flagged and true = correct,
    flagged and not true = incorrect, not flagged and true = missed, otherwise correct.
    Rerunning the local-model judgments can change a few flags, so the score must follow the run."""
    import hashlib
    sess = {}
    for line in open(os.path.join(HERE, "out", "sessions.jsonl")):
        d = json.loads(line)
        sess[hashlib.sha1(d["sid"].encode()).hexdigest()[:8]] = d
    changed = []
    for r in rows:
        d = sess[r["sid"]]
        fl = [f for f in FLAGS if d.get(f)]
        new = {"flags": ";".join(fl),
               "hidden_retry_substantive_flag": "yes" if d.get("hidden_retry_substantive") else "no"}
        for f in FLAGS:
            t = r[f"{f}_truth"] == "yes"
            new[f"{f}_verdict"] = ("correct" if t else "incorrect") if f in fl else ("missed" if t else "correct")
        diff = {k: (r[k], v) for k, v in new.items() if r[k] != v}
        if diff:
            changed.append((r["n"], r["sid"], diff))
            r.update(new)
    return changed


def score():
    """Precision and misses per flag, computed against the flags of the latest run.

    validation.csv holds one row per hand-read session with the reader's truth per flag
    ({flag}_truth) and the resulting verdict ({flag}_verdict: correct / incorrect / missed).
    The flag and verdict columns are refreshed from the latest run first (see _refresh)."""
    path = os.path.join(HERE, "validation.csv")
    rd = csv.DictReader(open(path))
    fields, rows = rd.fieldnames, list(rd)
    changed = _refresh(rows)
    if changed:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        for c in changed:
            print("refreshed row", *c, file=sys.stderr)
    res = {"sessions_read": len(rows), "by_group": {}}
    for fl in FLAGS:
        flagged = [r for r in rows if fl in r["flags"].split(";")]
        ok = sum(r[f"{fl}_verdict"] == "correct" for r in flagged)
        res[fl] = {"flagged_in_sample": len(flagged), "confirmed": ok,
                   "precision": round(ok / len(flagged), 3) if flagged else None,
                   "missed_in_sample": sum(r[f"{fl}_verdict"] == "missed" for r in rows),
                   "true_in_sample": sum(r[f"{fl}_truth"] == "yes" for r in rows)}
        t = res[fl]["true_in_sample"]
        res[fl]["recall"] = round((t - res[fl]["missed_in_sample"]) / t, 3) if t else None
    for g in sorted({r["group"] for r in rows}):
        gr = [r for r in rows if r["group"] == g]
        res["by_group"][g] = {"n": len(gr), **{fl: {v: sum(r[f"{fl}_verdict"] == v for r in gr)
                                                   for v in ("correct", "incorrect", "missed")} for fl in FLAGS}}
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(HERE, "out", "validation_score.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
