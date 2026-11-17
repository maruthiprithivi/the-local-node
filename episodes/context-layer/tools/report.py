"""Turn raw run JSONL files into CSVs, charts and a summary. Usage: report.py RUNS_DIR OUT_DIR BACKEND"""
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AXES = ("freshness", "identity_permission", "entity", "meaning_flip")


def pct(xs, q):
    xs = sorted(xs); k = (len(xs) - 1) * q; lo = int(k); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def main(runs, out, backend, prefix=None):
    runs, out = Path(runs), Path(out); out.mkdir(parents=True, exist_ok=True)
    recs = [json.loads(l) for p in sorted(runs.glob(f"{prefix or backend}-*.jsonl")) for l in p.read_text().splitlines()]
    ids = sorted({r["run_id"] for r in recs})
    from ctxlayer import workload as _wl
    kind_of = {e.id: e.kind for e in _wl.load().entities}
    KINDS = ("human", "agent", "mcp_server", "skill")
    traps = [r for r in recs if r["action"] == "trap" and r.get("scored")]
    rbs = [r for r in recs if r["action"] == "read_back"]
    # per probe csv
    with (out / "trap_probes.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["run_id", "axis", "asker", "about", "after", "ask", "pass", "missing", "leaked", "answer", "tokens_added", "ask_ms"])
        for r in traps:
            w.writerow([r["run_id"], r["axis"], r["asker"], r["about"], f'{r["probe"]["entity"]} {r["probe"]["event"]}', r["ask"],
                        int(r["pass"]), ";".join(r["missing"]), ";".join(r["leaked"]), ";".join(r["answer"]), r["tokens_added"], round(r["ask_s"] * 1000, 3)])
    # per trap (a trap passes when all its probes pass), per run, per axis
    tr = defaultdict(lambda: True)
    for r in traps:
        tr[(r["run_id"], r["axis"], r["asker"], r["about"], r["ask"])] &= r["pass"]
    axis_rows = []
    for ax in AXES:
        v = [ok for (rid, a, *_), ok in tr.items() if a == ax and rid == ids[0]]
        allv = [ok for (rid, a, *_), ok in tr.items() if a == ax]
        axis_rows.append((ax, sum(v), len(v), sum(allv), len(allv)))
    with (out / "trap_axes.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["axis", "traps_passed", "traps_total", "runs", "passed_all_runs", "total_all_runs"])
        for ax, p, n, pa, na in axis_rows:
            w.writerow([ax, p, n, len(ids), pa, na])
    # per subject kind (who the probe is about): trap axes, and read backs, over all runs
    by_kind = defaultdict(lambda: [0, 0])
    for r in traps:
        k = kind_of[r["probe"]["entity"]]
        by_kind[(r["axis"], k)][0] += r["pass"]; by_kind[(r["axis"], k)][1] += 1
    with (out / "trap_axes_by_kind.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["axis", "subject_kind", "probes_passed", "probes_total", "runs"])
        for ax in AXES:
            for k in KINDS:
                if by_kind[(ax, k)][1]:
                    w.writerow([ax, k, *by_kind[(ax, k)], len(ids)])
    rb_kind = defaultdict(lambda: [0, 0, 0])
    for r in rbs:
        k = kind_of[r["person"]]; rb_kind[k][0] += r["pass"]; rb_kind[k][1] += 1; rb_kind[k][2] += len(r["leaked"])
    with (out / "readbacks_by_kind.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["subject_kind", "readbacks_passed", "readbacks_total", "leaked_facts", "runs"])
        for k in KINDS:
            if rb_kind[k][1]:
                w.writerow([k, *rb_kind[k], len(ids)])
    # stale/leak and correctness from read backs
    leaks = sum(len(r["leaked"]) for r in rbs); miss = sum(len(r["missing"]) for r in rbs)
    rb_pass = sum(r["pass"] for r in rbs)
    # latency
    lat = {"read_back": [r["read_s"] * 1000 for r in rbs], "ask": [r["ask_s"] * 1000 for r in recs if r["action"] == "trap"],
           "write": [r["write_s"] * 1000 for r in recs if "write_s" in r]}
    setup = [r["setup_s"] for r in recs if "setup_s" in r]
    toks = [r["tokens_added"] for r in traps]
    with (out / "latency_ms.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["op", "n", "p50_ms", "p95_ms", "max_ms"])
        for k, xs in lat.items():
            w.writerow([k, len(xs), round(st.median(xs), 3), round(pct(xs, .95), 3), round(max(xs), 3)])
    with (out / "readbacks.csv").open("w", newline="") as f:
        w = csv.writer(f); w.writerow(["run_id", "step", "entity", "step_text", "pass", "missing", "leaked", "got"])
        for r in rbs:
            w.writerow([r["run_id"], r["step"], r["person"], r["text"], int(r["pass"]), ";".join(r["missing"]), ";".join(r["leaked"]), ";".join(r["got"])])
    # charts
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    labels = [a.replace("_", "/") for a, *_ in axis_rows]
    rates = [100 * pa / na for _, _, _, pa, na in axis_rows]
    bars = ax.bar(labels, rates, color=["#2a9d8f" if r == 100 else "#e76f51" if r < 50 else "#e9c46a" for r in rates])
    for b, (_, _, _, pa, na) in zip(bars, axis_rows):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2, f"{pa}/{na}", ha="center", fontsize=12)
    ax.set_ylim(0, 115); ax.set_ylabel("traps passed (%)")
    ax.set_title(f"{backend}: trap pass rate per axis (each axis scored alone)\n{len(ids)} runs, synthetic JML workload")
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(out / "trap_axes.png")
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    ops = list(lat); p50 = [st.median(lat[o]) for o in ops]; p95 = [pct(lat[o], .95) for o in ops]
    x = range(len(ops))
    ax.bar([i - .2 for i in x], p50, .4, label="p50", color="#264653"); ax.bar([i + .2 for i in x], p95, .4, label="p95", color="#2a9d8f")
    ax.set_xticks(list(x)); ax.set_xticklabels(ops); ax.set_ylabel("ms"); ax.legend()
    ax.set_title(f"{backend}: latency per operation (n={sum(map(len, lat.values()))} calls over {len(ids)} runs)")
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(out / "latency.png")
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
    cols = {"human": "#264653", "agent": "#2a9d8f", "mcp_server": "#e9c46a", "skill": "#e76f51"}
    kinds = [k for k in KINDS if any(by_kind[(a, k)][1] for a in AXES)]
    wd = .8 / max(len(kinds), 1)
    for j, k in enumerate(kinds):
        vals = [100 * by_kind[(a, k)][0] / by_kind[(a, k)][1] if by_kind[(a, k)][1] else 0 for a in AXES]
        bars = ax.bar([i + j * wd - .4 + wd / 2 for i in range(len(AXES))], vals, wd, label=k, color=cols[k])
        for b, a in zip(bars, AXES):
            if by_kind[(a, k)][1]:
                ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 2, f"{by_kind[(a, k)][0]}/{by_kind[(a, k)][1]}", ha="center", fontsize=7)
    ax.set_xticks(range(len(AXES))); ax.set_xticklabels([a.replace("_", "/") for a in AXES])
    ax.set_ylim(0, 118); ax.set_ylabel("probes passed (%)"); ax.legend(title="subject kind", ncol=4, loc="upper center", fontsize=8)
    ax.set_title(f"{backend}: probes passed per axis and subject kind ({len(ids)} runs)")
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout(); fig.savefig(out / "trap_axes_by_kind.png")
    # summary
    L = [f"# {backend} summary", "", f"Runs: {len(ids)}", ""] + [f"- `{i}`" for i in ids] + ["",
         f"Read backs: {rb_pass}/{len(rbs)} passed, {leaks} leaked facts, {miss} missing facts (stale-access / read-back-after-delete, all runs).", "",
         "## Trap axes (first run; all-run totals in trap_axes.csv)", "", "| axis | passed | total | all runs |", "|---|---|---|---|"]
    L += [f"| {a} | {p} | {n} | {pa}/{na} |" for a, p, n, pa, na in axis_rows]
    L += ["", "## Read backs by subject kind (all runs)", "", "| kind | passed | total | leaked facts |", "|---|---|---|---|"]
    L += [f"| {k} | {rb_kind[k][0]} | {rb_kind[k][1]} | {rb_kind[k][2]} |" for k in KINDS if rb_kind[k][1]]
    L += ["", "## Probes by axis and subject kind (all runs; a trap can have two probes)", "", "| axis | kind | passed | total |", "|---|---|---|---|"]
    L += [f"| {a} | {k} | {by_kind[(a, k)][0]} | {by_kind[(a, k)][1]} |" for a in AXES for k in KINDS if by_kind[(a, k)][1]]
    L += ["", "## Latency (ms)", "", "| op | n | p50 | p95 |", "|---|---|---|---|"]
    L += [f"| {k} | {len(v)} | {st.median(v):.2f} | {pct(v, .95):.2f} |" for k, v in lat.items()]
    L += ["", f"Setup (container up to schema ready, adapter side): median {st.median(setup):.3f} s over {len(setup)} runs.",
          f"Tokens added per trap answer (approximate, regex pieces): mean {st.mean(toks):.1f}, max {max(toks)}."]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main(*sys.argv[1:5])
