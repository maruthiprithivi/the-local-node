#!/usr/bin/env python3
"""LFM3 tool-loop check: how many chained tool calls does a model complete with long tool results fed back?
Stdlib only. Runs inside the client sandbox; talks only to the model server (OpenAI-compatible /v1/chat/completions, native tools).
Usage: toolloop.py BASE_URL MODEL SEED CTX OUT_JSON [--cap 50] [--filler-lines 110]
Each tool result = ~2.5-3.5K tokens of deterministic filler (synthetic log lines) + a final line naming the exact next call.
Ground truth per step is generated from SEED, so a run is reproducible and every call is checkable.
Strict scoring: the first deviation ends the count. After a deviation the driver feeds back a neutral error for up to 2 more
turns only to characterise behaviour (loop? recovery?); that never changes the count."""
import json, random, sys, time, urllib.request, urllib.error, argparse, string

ap = argparse.ArgumentParser()
ap.add_argument("base"); ap.add_argument("model"); ap.add_argument("seed", type=int); ap.add_argument("ctx", type=int); ap.add_argument("out")
ap.add_argument("--cap", type=int, default=50); ap.add_argument("--filler-lines", type=int, default=110)
ap.add_argument("--temperature", type=float, default=0.6); ap.add_argument("--top-p", type=float, default=0.95); ap.add_argument("--top-k", type=int, default=20)
ap.add_argument("--max-tokens", type=int, default=2048); ap.add_argument("--post-break-turns", type=int, default=2)
a = ap.parse_args()

TOOLS = [
 {"type": "function", "function": {"name": "read_file", "description": "Read a text file from the document store.",
   "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Absolute file path"}}, "required": ["path"]}}},
 {"type": "function", "function": {"name": "search", "description": "Full-text search over the document store.",
   "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]}}},
 {"type": "function", "function": {"name": "next_step", "description": "Submit a step token to the workflow engine and get the next step.",
   "parameters": {"type": "object", "properties": {"token": {"type": "string", "description": "Step token"}}, "required": ["token"]}}},
 {"type": "function", "function": {"name": "get_record", "description": "Fetch a database record by numeric id.",
   "parameters": {"type": "object", "properties": {"record_id": {"type": "integer", "description": "Record id"}}, "required": ["record_id"]}}},
]
ARGKEY = {"read_file": "path", "search": "query", "next_step": "token", "get_record": "record_id"}
WORDS = ("ledger invoice shard replica cache window vector bucket lease quota cursor batch tenant region worker queue "
         "socket packet frame index schema commit branch merge rebase kernel driver buffer stream signal").split()

rng = random.Random(1000 + a.seed)
def make_arg(tool):
    if tool == "read_file": return f"/data/{rng.choice(WORDS)}-{rng.randint(10,99)}/notes-{rng.randint(1000,9999)}.txt"
    if tool == "search": return f"{rng.choice(WORDS)} {rng.choice(WORDS)} {rng.randint(1000,9999)}"
    if tool == "next_step": return "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(4)) + "-" + "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return rng.randint(10000, 99999)
# plan[i] = (tool, arg) for call i (0-based). Call 0 is given in the user prompt. Tool order is seeded-random (no fixed cycle),
# never the same tool twice in a row.
plan = []; prev = None
for i in range(a.cap):
    t = rng.choice([x for x in ARGKEY if x != prev]); prev = t; plan.append((t, make_arg(t)))
final_word = rng.choice(WORDS).upper() + str(rng.randint(100, 999))

frng = random.Random(5000 + a.seed)
def filler(step):
    lines = []
    for j in range(a.filler_lines):
        lines.append(f"2026-10-{frng.randint(10,28)} {frng.randint(0,23):02d}:{frng.randint(0,59):02d}:{frng.randint(0,59):02d} "
                     f"{frng.choice(['INFO','DEBUG','WARN','INFO','TRACE'])} {frng.choice(WORDS)}-{frng.randint(1,64)} "
                     f"{frng.choice(['processed','flushed','rebalanced','skipped','merged','retried'])} {frng.choice(WORDS)} "
                     f"id={frng.randint(100000,999999)} took={frng.randint(1,900)}ms queue={frng.randint(0,80)} "
                     f"note=\"{' '.join(frng.choice(WORDS) for _ in range(5))}\"")
    return "\n".join(lines)
def fmt_args(tool, arg): return json.dumps({ARGKEY[tool]: arg})
def tool_result(i):
    """Result of the correct call i: filler + instruction for call i+1 (or DONE)."""
    head = f"=== result of {plan[i][0]} (record {i+1}) ===\n"
    if i + 1 < a.cap:
        t, arg = plan[i + 1]
        tail = f"\n=== end of data ===\nNEXT ACTION: call the tool `{t}` with arguments {fmt_args(t, arg)}"
    else:
        tail = f"\n=== end of data ===\nDONE. No more tool calls. Reply with only this final word: {final_word}"
    return head + filler(i) + tail

def post(body, timeout=600):
    req = urllib.request.Request(a.base + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return 200, json.loads(r.read())
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="replace")
        try: return e.code, json.loads(txt)
        except Exception: return e.code, {"raw": txt[:2000]}
    except Exception as e: return -1, {"exception": repr(e)}

# wait for server
for _ in range(180):
    try:
        with urllib.request.urlopen(a.base + "/health", timeout=5) as r:
            if r.status == 200: break
    except Exception: pass
    time.sleep(2)

SYSTEM = ("You are an automation agent with tools. Work strictly one tool call at a time. Every tool result ends with a line "
          "'NEXT ACTION: ...' that names exactly one tool and its exact arguments. Make exactly that call next, with exactly those "
          "argument values, and nothing else. Ignore the rest of the tool output. Keep going until a result says DONE; then reply with the final word it asks for.")
t0, a0 = plan[0]
USER = f"Start the workflow. NEXT ACTION: call the tool `{t0}` with arguments {fmt_args(t0, a0)}"
msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": USER}]

def check(tool, raw_args, i):
    """Return (ok, kind, detail) for a call against plan[i]."""
    et, ea = plan[i]; key = ARGKEY[et]
    try: args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except Exception as e: return False, "invalid_json_args", f"{e}: {str(raw_args)[:300]}"
    if not isinstance(args, dict): return False, "invalid_json_args", f"not an object: {str(raw_args)[:300]}"
    if tool not in ARGKEY: return False, "wrong_tool", f"unknown tool {tool!r} (expected {et})"
    if tool != et: return False, "wrong_tool", f"called {tool} (expected {et})"
    if key not in args: return False, "malformed_args", f"missing key {key}: {raw_args}"
    v = args[key]
    if et == "get_record":
        try: good = int(v) == ea
        except Exception: good = False
    else: good = isinstance(v, str) and v.strip() == ea
    if not good: return False, "wrong_args", f"{key}={v!r} (expected {ea!r})"
    extra = sorted(set(args) - {key})
    return True, "ok", ("extra keys " + ",".join(extra)) if extra else ""

log = {"seed": a.seed, "ctx": a.ctx, "cap": a.cap, "filler_lines": a.filler_lines, "model": a.model,
       "sampling": {"temperature": a.temperature, "top_p": a.top_p, "top_k": a.top_k, "seed": a.seed, "max_tokens": a.max_tokens},
       "plan": plan, "final_word": final_word, "turns": [], "started": time.time()}
completed = 0; brk = None; post_turns = 0; seen_calls = []; last_usage = None
def save():
    log["calls_completed"] = completed; log["break"] = brk; log["wall_s"] = round(time.time() - log["started"], 2)
    log["last_usage"] = last_usage
    json.dump(log, open(a.out, "w"), indent=1)

while True:
    body = {"model": a.model, "messages": msgs, "tools": TOOLS, "tool_choice": "auto", "temperature": a.temperature,
            "top_p": a.top_p, "top_k": a.top_k, "seed": a.seed, "max_tokens": a.max_tokens, "stream": False}
    ts = time.time(); code, resp = post(body); dt = round(time.time() - ts, 3)
    turn = {"i": completed, "http": code, "dt": dt}
    if code != 200 or "choices" not in resp:
        turn["error"] = resp; log["turns"].append(turn)
        if brk is None:
            brk = {"kind": "server_error_or_ctx_overflow", "at_call": completed + 1, "detail": json.dumps(resp)[:1500], "http": code}
        break
    ch = resp["choices"][0]; m = ch["message"]; u = resp.get("usage", {}); last_usage = u
    turn.update({"finish": ch.get("finish_reason"), "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                 "content": (m.get("content") or "")[:600], "reasoning_len": len(m.get("reasoning_content") or ""), "reasoning_head": (m.get("reasoning_content") or "")[:1500], "reasoning_tail": (m.get("reasoning_content") or "")[-1500:],
                 "tool_calls": [{"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]} for tc in (m.get("tool_calls") or [])],
                 "timings": resp.get("timings")})
    log["turns"].append(turn)
    tcs = m.get("tool_calls") or []
    if brk is not None:  # post-break observation only
        post_turns += 1
        if not tcs or post_turns >= a.post_break_turns: break
        msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": tcs})
        for tc in tcs: msgs.append({"role": "tool", "tool_call_id": tc.get("id", "x"), "content": "Error: invalid call."})
        continue
    if completed >= a.cap:  # expected final answer
        if tcs: brk = {"kind": "kept_calling_after_done", "at_call": completed + 1, "detail": json.dumps(turn["tool_calls"])[:500]}
        else:
            ok = final_word in (m.get("content") or "")
            brk = {"kind": "reached_cap_" + ("final_ok" if ok else "final_wrong"), "at_call": None, "detail": (m.get("content") or "")[:300]}
        break
    if not tcs:
        c = (m.get("content") or "")
        kind = "max_tokens_no_call" if ch.get("finish_reason") == "length" else ("malformed_call_in_text" if ("tool_call" in c or '"name"' in c or "read_file(" in c or "search(" in c or "next_step(" in c or "get_record(" in c) else "stopped_calling")
        brk = {"kind": kind, "at_call": completed + 1, "detail": c[:500]}
        break
    tc = tcs[0]; name = tc["function"]["name"]; raw = tc["function"]["arguments"]
    ok, kind, detail = check(name, raw, completed)
    sig = (name, raw if isinstance(raw, str) else json.dumps(raw, sort_keys=True))
    if not ok:
        try: sig2 = (name, json.dumps(json.loads(raw), sort_keys=True))
        except Exception: sig2 = sig
        reps = sum(1 for s in seen_calls if s == sig2)
        if reps >= 1: kind = "repeat_earlier_call" + (" (3x loop)" if reps >= 2 else "")
        brk = {"kind": kind, "at_call": completed + 1, "detail": detail, "expected": plan[completed]}
        msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": tcs})
        for t in tcs: msgs.append({"role": "tool", "tool_call_id": t.get("id", "x"), "content": "Error: invalid call."})
        if a.post_break_turns <= 0: break
        save(); continue
    try: seen_calls.append((name, json.dumps(json.loads(raw), sort_keys=True)))
    except Exception: seen_calls.append(sig)
    if len(tcs) > 1: turn["note"] = f"{len(tcs)} parallel calls; first was correct, extras answered 'one call at a time'"
    completed += 1
    msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": tcs})
    msgs.append({"role": "tool", "tool_call_id": tc.get("id", "x"), "content": tool_result(completed - 1)})
    for t in tcs[1:]: msgs.append({"role": "tool", "tool_call_id": t.get("id", "x"), "content": "Ignored: make one call at a time."})
    print(f"call {completed} ok {name} prompt_tokens={u.get('prompt_tokens')} dt={dt}", flush=True)
    save()
save()
print("RESULT", json.dumps({"seed": a.seed, "ctx": a.ctx, "calls_completed": completed, "break": brk, "wall_s": log["wall_s"], "last_usage": last_usage}), flush=True)
