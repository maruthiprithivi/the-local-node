#!/usr/bin/env python3
"""Recover dsh-superagent sessions that the log packer overwrote.

In MANIFEST.csv, 17 'b-*' runs list two sessions (main + delegated subagent) with
the same dest_path, so only one file survived. This reads each run's coll.tar,
extracts ONLY files named session.v4.jsonl.zstd (never credentials), decompresses
them, and writes every session that is not already in logs/ to ../recovered/.
It also writes ../recovered/RECOVERED.csv with manifest-style rows.

    /path/to/python-with-zstandard -m replay.recover --runs <evidence/runs dir>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tarfile

import zstandard

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=os.path.join(HERE, "..", "logs"))
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "recovered"))
    a = ap.parse_args()
    rows = list(csv.DictReader(open(os.path.join(a.logs, "MANIFEST.csv"))))
    seen = {}
    for r in rows:
        seen.setdefault(r["dest_path"], []).append(r)
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    os.makedirs(a.out, exist_ok=True)
    out_rows = []
    for dest, rs in sorted(dup.items()):
        run = rs[0]["task"]
        have = open(os.path.join(a.logs, dest.split("/", 1)[1]), "rb").read()
        have_h = hashlib.sha256(have).hexdigest()
        tar = os.path.join(a.runs, run, "dl", "coll.tar")
        with tarfile.open(tar) as tf:
            for m in tf.getmembers():
                if not m.name.endswith("session.v4.jsonl.zstd") or ".." in m.name.split("/"):
                    continue
                raw = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(tf.extractfile(m).read())).read()
                if hashlib.sha256(raw).hexdigest() == have_h:
                    continue  # this one survived in logs/
                first = json.loads(raw.split(b"\n", 1)[0])
                origin = first.get("origin") or "main"
                name = f"{run}__{origin}__{first.get('id', 'unknown')}.session.jsonl"
                with open(os.path.join(a.out, name), "wb") as f:
                    f.write(raw)
                r = dict(rs[0])
                r["session_id"] = f"{run}/session-{origin}-recovered"
                r["dest_path"] = "recovered/" + name
                r["bytes"] = str(len(raw))
                r["notes"] = "Recovered from coll.tar by kit/replay/recover.py (packer had overwritten it)"
                out_rows.append(r)
    with open(os.path.join(a.out, "RECOVERED.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(len(dup), "duplicated dest paths;", len(out_rows), "sessions recovered")


if __name__ == "__main__":
    main()
