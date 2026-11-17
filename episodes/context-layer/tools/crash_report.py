"""Turn the per rep verify JSON of a crash batch into results.csv and summary.md. Usage: crash_report.py <batch dir>"""
import csv
import json
import statistics
import sys
from pathlib import Path

COLS = ["mode", "rep", "jml_changes_acked", "tail_writes_acked", "records_expected", "records_recovered", "records_lost",
        "jml_records_expected", "jml_records_recovered", "stale_resurfaced", "unacked_tail_present", "last_ack_to_kill_s", "restart_ready_s"]


def main(d):
    d = Path(d)
    rows = [json.loads(p.read_text()) for p in sorted(d.glob("*.verify.json"))]
    rows.sort(key=lambda r: (r["mode"], r["rep"]))
    with (d / "results.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(COLS); [w.writerow([r[c] for c in COLS]) for r in rows]
    out = [f"# Crash durability, relate (Neo4j Community), batch {d.name}", "",
           "| mode | reps | writes acked (JML + tail) | records expected | recovered | lost | stale resurfaced | last ack to kill s (median) | restart to ready s (median) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for mode in sorted({r["mode"] for r in rows}):
        rs = [r for r in rows if r["mode"] == mode]
        s = lambda k: sum(r[k] for r in rs)
        out.append(f"| {mode} | {len(rs)} | {s('jml_changes_acked')} + {s('tail_writes_acked')} | {s('records_expected')} | "
                   f"{s('records_recovered')} | {s('records_lost')} | {s('stale_resurfaced')} | "
                   f"{statistics.median(r['last_ack_to_kill_s'] for r in rs):.2f} | {statistics.median(r['restart_ready_s'] for r in rs):.2f} |")
    (d / "summary.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1])
