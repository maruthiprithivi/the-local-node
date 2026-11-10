"""Prompt-trim analysis: per-run and per-level stats from run.json + requests.jsonl (raw request logs)."""
import json, glob, statistics as st, sys, os
O = sys.argv[1]
rows = []
for f in sorted(glob.glob(f"{O}/artifacts/*/run.json")):
    j = json.load(open(f)); d = os.path.dirname(f)
    att = sorted(glob.glob(f"{d}/attempt-*"))[-1]
    reqs = [json.loads(l) for l in open(f"{att}/log/requests.jsonl")]
    ok = [r for r in reqs if r.get("status") == 200 and isinstance(r.get("response"), dict) and r["response"].get("usage")]
    us = [r["response"]["usage"] for r in ok]
    pt = [u["prompt_tokens"] for u in us]
    sysc = next((m["content"] for m in reqs[0]["request"]["messages"] if m["role"] == "system"), "")
    if isinstance(sysc, list): sysc = "".join(p.get("text", "") for p in sysc)
    ttft = [r["ttft_s"] for r in ok if r.get("ttft_s") is not None]
    rows.append({"harness": j["harness"], "item": j["item"], "seed": j["seed"], "status": j["status"],
                 "strict": bool(j["strict_pass"]), "lenient": bool(j["lenient_pass"]), "wall_s": j["wall_s"],
                 "attempts": j["attempts"], "requests": len(reqs), "requests_ok": len(ok),
                 "prompt_tokens_total": sum(pt), "prompt_tokens_per_req_mean": round(sum(pt) / len(pt), 1) if pt else None,
                 "first_req_prompt_tokens": pt[0] if pt else None, "system_prompt_chars": len(sysc),
                 "ttft_median_s": round(st.median(ttft), 3) if ttft else None, "first_req_ttft_s": ttft[0] if ttft else None,
                 "completion_tokens": j["completion_tokens"], "budget_hit": j["budget_hit"], "timed_out": j["timed_out"]})
def mr(v):
    v = [x for x in v if x is not None]
    return {"median": round(st.median(v), 3), "min": min(v), "max": max(v), "n": len(v)} if v else None
lv = {}
for h in sorted({r["harness"] for r in rows}):
    R = [r for r in rows if r["harness"] == h]
    lv[h] = {"runs": len(R), "strict_pass": sum(r["strict"] for r in R), "lenient_pass": sum(r["lenient"] for r in R),
             "system_prompt_chars": mr([r["system_prompt_chars"] for r in R]),
             "first_req_prompt_tokens": mr([r["first_req_prompt_tokens"] for r in R]),
             "prompt_tokens_per_req_mean": mr([r["prompt_tokens_per_req_mean"] for r in R]),
             "prompt_tokens_total": mr([r["prompt_tokens_total"] for r in R]),
             "requests": mr([r["requests"] for r in R]), "ttft_median_s": mr([r["ttft_median_s"] for r in R]),
             "first_req_ttft_s": mr([r["first_req_ttft_s"] for r in R]), "wall_s": mr([r["wall_s"] for r in R]),
             "completion_tokens": mr([r["completion_tokens"] for r in R]),
             "budget_hits": sum(bool(r["budget_hit"]) for r in R), "timeouts": sum(bool(r["timed_out"]) for r in R),
             "fails": [f'{r["item"]} s{r["seed"]} {r["status"]}' for r in R if not r["strict"]]}
json.dump({"runs": rows, "levels": lv}, open(sys.argv[2], "w"), indent=1)
print(json.dumps(lv, indent=1))
