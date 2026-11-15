#!/usr/bin/env python3
import json, sys
from pathlib import Path
root = Path(sys.argv[1] if len(sys.argv) > 1 else "runs")
rows = []
for p in sorted(root.glob("trial-*/result.json")):
    d = json.loads(p.read_text())
    rows.append(d)
print("| run | pass/fail | wall s | test after | commits | error |")
print("| --- | --- | --- | --- | --- | --- |")
for d in rows:
    status = "PASS" if d.get("passed") else "FAIL"
    wall = f"{d.get('wallMs', 0)/1000:.1f}"
    err = (d.get("error") or "").split("\n", 1)[0][:80] or "-"
    print(f"| {d.get('runId')} | {status} | {wall} | {d.get('testAfterExit')} | {d.get('commitCount')} | {err} |")
if not rows:
    print("| (no trials yet) | - | - | - | - | - |")
