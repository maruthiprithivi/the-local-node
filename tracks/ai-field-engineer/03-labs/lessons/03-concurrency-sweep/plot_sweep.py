"""
Lesson 03 — draw the sweep: throughput up, TTFT knee, capacity line.

Reads results/03-sweep.csv (the latest run per target) and writes
results/03-sweep.png. Without matplotlib it prints a text chart instead.

    python plot_sweep.py
"""
import csv
from pathlib import Path

from felab.results import RESULTS

path = RESULTS / "03-sweep.csv"
if not path.exists():
    raise SystemExit("No results yet — run sweep.py first.")

rows = list(csv.DictReader(path.open()))
# Keep only the most recent sweep for each target (a sweep restarts at conc=1).
latest: dict[str, list[dict]] = {}
for r in rows:
    if r["conc"] == "1":
        latest[r["target"]] = []
    latest.setdefault(r["target"], []).append(r)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    for tgt, rs in latest.items():
        print(f"\n{tgt}   (█ = aggregate tok/s, · = TTFT p95 ms)")
        top = max(float(r["agg_tok_s"]) for r in rs)
        for r in rs:
            bar = "█" * int(40 * float(r["agg_tok_s"]) / top)
            print(f"  C={r['conc']:>3} {bar:<40} {float(r['agg_tok_s']):7.0f} tok/s · {float(r['ttft_p95']):6.0f} ms")
    raise SystemExit

fig, ax1 = plt.subplots(figsize=(9, 5))
ax2 = ax1.twinx()
for tgt, rs in latest.items():
    c = [int(r["conc"]) for r in rs]
    ax1.plot(c, [float(r["agg_tok_s"]) for r in rs], "-o", label=f"{tgt} aggregate tok/s")
    ax2.plot(c, [float(r["ttft_p95"]) for r in rs], "--s", label=f"{tgt} TTFT p95")
    slo = float(rs[0]["slo_ms"])
ax2.axhline(slo, color="red", lw=1, ls=":")
ax2.text(c[0], slo * 1.03, f"SLO {slo:.0f} ms", color="red", fontsize=9)
ax1.set_xscale("log", base=2)
ax1.set_xticks(c)
ax1.set_xticklabels([str(x) for x in c])
ax1.set_xlabel("concurrent requests")
ax1.set_ylabel("aggregate tokens / s  (solid)")
ax2.set_ylabel("TTFT p95, ms  (dashed)")
ax1.set_title("Throughput rises, then the queue arrives")
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
out = Path(RESULTS / "03-sweep.png")
fig.tight_layout()
fig.savefig(out, dpi=130)
print(f"saved → {out}")
