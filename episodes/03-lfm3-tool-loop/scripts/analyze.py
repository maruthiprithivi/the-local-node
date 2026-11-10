import json, glob, statistics, csv, sys, os
R = sys.argv[1]; rows = []
for f in sorted(glob.glob(f"{R}/run-c*-s*.json"), key=lambda p: (int(p.split('-c')[1].split('-')[0]), p)):
    d = json.load(open(f)); b = d["break"] or {}
    ok_turns = [t for t in d["turns"] if t.get("http") == 200]
    lastp = max([t.get("prompt_tokens") or 0 for t in d["turns"]] + [0])
    # tokens at break: overflow -> n_prompt_tokens from error; else prompt+completion of the breaking turn
    bt = None
    for t in d["turns"]:
        if t.get("i") == d["calls_completed"]: bt = t; break
    if bt and bt.get("http") != 200:
        ctxb = (bt.get("error", {}).get("error", {}) or {}).get("n_prompt_tokens")
    elif bt: ctxb = (bt.get("prompt_tokens") or 0) + (bt.get("completion_tokens") or 0)
    else: ctxb = None
    post = [t for t in d["turns"] if t.get("i") == d["calls_completed"]][1:]
    rows.append({"ctx": d["ctx"], "seed": d["seed"], "calls": d["calls_completed"], "break": b.get("kind"), "detail": (b.get("detail") or "")[:160],
                 "expected": b.get("expected"), "tokens_at_break": ctxb, "wall_s": d["wall_s"], "turns": len(d["turns"]),
                 "post_break": [(t.get("tool_calls"), (t.get("content") or "")[:80], t.get("finish")) for t in post],
                 "break_turn_reasoning_len": bt.get("reasoning_len") if bt else None, "break_turn_finish": bt.get("finish") if bt else None,
                 "parallel_notes": sum(1 for t in d["turns"] if t.get("note"))})
for r in rows: print(json.dumps(r))
by = {}
for r in rows: by.setdefault(r["ctx"], []).append(r["calls"])
for c, v in by.items(): print(f"ctx {c}: calls {v} median {statistics.median(v)} range {min(v)}-{max(v)}")
allv = [r["calls"] for r in rows]; print("all:", allv, "median", statistics.median(allv))
m = list(csv.DictReader(open(f"{R}/mem.csv")))
pk = max(m, key=lambda x: float(x["host_used_gib"])); pg = max(m, key=lambda x: int(x["llama_gpu_mib"])); pa = max(m, key=lambda x: int(x["gpu_apps_mib"]))
pc = max(m, key=lambda x: int(x["srv_cgroup_bytes"]))
print("samples", len(m), "host peak", pk["host_used_gib"], pk["host_pct"], pk["ts"], "| llama GPU peak MiB", pg["llama_gpu_mib"], pg["ts"], "| all GPU apps peak", pa["gpu_apps_mib"], "| srv cgroup peak", pc["srv_cgroup_bytes"], pc["ts"])
print("host min", min(float(x["host_used_gib"]) for x in m))
json.dump(rows, open(f"{R}/summary.json", "w"), indent=1)
