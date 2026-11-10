"""Decode-speed client (stdlib only; runs in an isolated container on an internal-only docker network).
usage: client.py BASE_URL MODEL LABEL OUTJSON [--rounds-idle 5] [--rounds-conc 3] [--qos-header]"""
import json, random, sys, threading, time, urllib.request, argparse
ap = argparse.ArgumentParser(); ap.add_argument("base"); ap.add_argument("model"); ap.add_argument("label"); ap.add_argument("out")
ap.add_argument("--rounds-idle", type=int, default=5); ap.add_argument("--rounds-conc", type=int, default=3)
ap.add_argument("--qos-header", action="store_true"); ap.add_argument("--agent-tokens", type=int, default=7500)
a = ap.parse_args()
def _models():
    for _ in range(1800):
        try:
            return [m["id"] for m in json.load(urllib.request.urlopen(a.base + "/v1/models", timeout=10))["data"]]
        except Exception:
            time.sleep(1)
    raise SystemExit("server never answered /v1/models")
_ids = _models(); print("models", _ids, flush=True)
if a.model == "auto": a.model = _ids[0]
WORDS = ("system kernel memory buffer process thread socket packet route cache disk block inode journal mutex lock queue "
         "signal handler driver device module config parser token lexer grammar syntax compiler linker loader symbol "
         "binary object stack heap pointer register branch vector matrix tensor gradient layer weight bias kernel").split()
def doc(seed, ntok):
    r = random.Random(seed); out = []
    # ~1.3 tokens per word for these words; sentences of 12 words
    for i in range(int(ntok / 2.6 / 12)):  # measured: ~2.6 tokens/word with this tokenizer (first try gave 14.85k for 7.5k)
        out.append(" ".join(r.choice(WORDS) for _ in range(12)).capitalize() + f" (note {seed}-{i}).")
    return " ".join(out)
def stream(messages, max_tokens, headers=None, tag=""):
    body = {"model": a.model, "messages": messages, "max_tokens": max_tokens, "stream": True, "temperature": 0.0,
            "stream_options": {"include_usage": True}}
    req = urllib.request.Request(a.base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", **(headers or {})})
    t0 = time.time(); first = None; last = None; n = 0; usage = None; err = None
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            for line in resp:
                line = line.strip()
                if not line.startswith(b"data:"): continue
                d = line[5:].strip()
                if d == b"[DONE]": break
                j = json.loads(d)
                if j.get("usage"): usage = j["usage"]
                for c in j.get("choices") or []:
                    dl = c.get("delta") or {}
                    if dl.get("content") or dl.get("reasoning_content") or dl.get("reasoning"):
                        now = time.time(); n += 1; last = now
                        if first is None: first = now
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:300]
    t1 = time.time()
    ct = (usage or {}).get("completion_tokens"); pt = (usage or {}).get("prompt_tokens")
    toks = ct if ct else n
    dec = ((toks - 1) / (last - first)) if (first and last and last > first and toks > 1) else None
    return {"tag": tag, "t_send": t0, "ttft_s": (first - t0) if first else None, "total_s": t1 - t0, "chunks": n,
            "completion_tokens": ct, "prompt_tokens": pt, "decode_tok_s": dec, "err": err}
res = {"label": a.label, "model": a.model, "idle": [], "decode": [], "conc": []}
def save(): json.dump(res, open(a.out, "w"), indent=1)
# warm-up (discarded)
print("warmup", stream([{"role": "user", "content": "Say hi."}], 16), flush=True)
nonce = random.Random(time.time()).randint(0, 10**9)
for i in range(a.rounds_idle):
    r = stream([{"role": "user", "content": f"[{nonce}-{i}] In one sentence, what is a mutex?"}], 32, tag="idle-short"); res["idle"].append(r)
    print("idle", round(r["ttft_s"] or -1, 3), r["err"], flush=True); time.sleep(1)
    r = stream([{"role": "user", "content": f"[{nonce}-{i}] Write a detailed 600-word essay on how operating system schedulers work."}], 512, tag="decode"); res["decode"].append(r)
    print("decode", r["decode_tok_s"], r["completion_tokens"], r["err"], flush=True); save(); time.sleep(1)
for k in range(a.rounds_conc):
    agents = []; th = []
    def agent(j):
        r = stream([{"role": "user", "content": doc(nonce * 100 + k * 10 + j, a.agent_tokens) + "\n\nSummarize the document above in five bullet points."}], 256, tag=f"agent{j}")
        agents.append(r)
    t0 = time.time()
    for j in range(8):
        t = threading.Thread(target=agent, args=(j,)); t.start(); th.append(t)
    time.sleep(2.0)
    hdr = {"x-superfluid-qos": "interactive"} if a.qos_header else None
    chat = stream([{"role": "user", "content": f"[{nonce}-{k}] Quick question: what is 17 times 3? Answer with the number only."}], 32, headers=hdr, tag="chat")
    for t in th: t.join()
    rec = {"round": k, "chat": chat, "agents": sorted(agents, key=lambda x: x["tag"]), "wall_s": time.time() - t0,
           "agents_ok": sum(1 for x in agents if not x["err"] and (x["completion_tokens"] or x["chunks"]))}
    res["conc"].append(rec); save()
    print("conc", k, "chat_ttft", chat["ttft_s"], "agents_ok", rec["agents_ok"], "wall", round(rec["wall_s"], 1),
          "agent_pt", [x["prompt_tokens"] for x in rec["agents"]][:2], flush=True)
    time.sleep(5)
save(); print("DONE", flush=True)
