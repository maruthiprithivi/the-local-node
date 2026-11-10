"""Pooled per-request stats per prompt level, from a run directory laid out as
<OUT>/artifacts/<run>/attempt-*/log/requests.jsonl (one JSON object per model request, OpenAI-style usage in response.usage,
ttft_s measured by the logging proxy). The run directory name must contain the harness name, e.g. qwen-p100.
Usage: pooled.py OUT [LEVEL ...]   (default levels: qwen-p100 qwen-p60 qwen-p30 qwen-pmin)"""
import glob, json, statistics as st, sys
O = sys.argv[1]; levels = sys.argv[2:] or ["qwen-p100", "qwen-p60", "qwen-p30", "qwen-pmin"]
def p95(v):  # statistics.quantiles default (exclusive) method, as in the published numbers
    return st.quantiles(v, n=20)[18]
out = {}
for lv in levels:
    reqs = []
    for f in glob.glob(f"{O}/artifacts/*__{lv}__*/attempt-*/log/requests.jsonl"):
        reqs += [json.loads(l) for l in open(f)]
    ok = [r for r in reqs if r.get("status") == 200 and isinstance(r.get("response"), dict) and r["response"].get("usage")]
    pt = [r["response"]["usage"]["prompt_tokens"] for r in ok]
    ca = [((r["response"]["usage"].get("prompt_tokens_details") or {}).get("cached_tokens") or 0) for r in ok]
    tt = [r["ttft_s"] for r in ok if r.get("ttft_s") is not None]
    out[lv] = {"requests": len(reqs), "requests_ok": len(ok), "prompt_tokens_per_req_median": st.median(pt),
               "ttft_median_s": round(st.median(tt), 3), "ttft_p95_s": round(p95(tt), 2),
               "uncached_tokens_per_req_median": st.median([p - c for p, c in zip(pt, ca)]),
               "cached_share_pct": round(100 * sum(ca) / sum(pt), 1)}
print(json.dumps(out, indent=1))
