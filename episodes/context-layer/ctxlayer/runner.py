"""Execute a plan against a ready backend and write raw outputs as JSON lines.
Each read back records what came out, what was expected, and the facts that leaked.
Each trap probe is scored pass or fail against ground truth written in the workload."""
import json
import random
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from . import plan


def git_sha():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip() or "nogit"
    except OSError:
        return "nogit"


def new_run_id(backend, seed, n=1):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{backend}-{ts}-seed{seed}-{git_sha()}-r{n}"


def approx_tokens(facts):
    """Rough tokens a memory answer adds to a prompt: word and number pieces of the rendered context.
    An approximation, not a model tokenizer. Same function for every backend."""
    return len(re.findall(r"[A-Za-z0-9]+|[^\sA-Za-z0-9]", "; ".join(sorted(facts))))


def score_probe(probe, answer):
    ans = set(answer)
    if probe.get("empty"):
        return {"missing": [], "leaked": sorted(ans), "pass": not ans}
    missing = sorted(set(probe.get("has", [])) - ans)
    leaked = sorted(set(probe.get("lacks", [])) & ans)
    return {"missing": missing, "leaked": leaked, "pass": not missing and not leaked}


def run(wl, backend, entity_filter=None, out="runs", run_id=None):
    random.seed(wl.seed)
    steps = plan.build(wl, backend, entity_filter)
    a = backend.make()
    run_id = run_id or new_run_id(backend.name, wl.seed)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    path = out / f"{run_id}.jsonl"
    with path.open("w") as f:
        for i, s in enumerate(steps, 1):
            rec = {"run_id": run_id, "backend": backend.name, "step": i, "action": s.action, "person": s.person, "text": s.text}
            t0 = time.perf_counter()
            if s.action == "setup" and i == 1:
                a.setup()
                rec["setup_s"] = time.perf_counter() - t0
            elif s.action == "write":
                a.write(s.person, s.facts); rec["write_s"] = time.perf_counter() - t0
            elif s.action == "revoke":
                a.revoke(s.person, s.facts); rec["write_s"] = time.perf_counter() - t0
            elif s.action == "forget":
                a.forget(s.person); rec["write_s"] = time.perf_counter() - t0
            elif s.action == "read_back":
                got = set(a.read_back(s.person)); rec["read_s"] = time.perf_counter() - t0
                rec["got"] = sorted(got)
                rec["missing"] = sorted(set(s.expect_has) - got)
                rec["leaked"] = sorted(set(s.expect_lacks) & got)
                rec["pass"] = not rec["missing"] and not rec["leaked"]
            elif s.action == "trap":
                t, pr = s.trap, s.probe
                ans = a.ask(t.asker, t.ask, t.about); rec["ask_s"] = time.perf_counter() - t0
                rec.update(axis=t.axis, asker=t.asker, about=t.about, ask=t.ask, probe=pr,
                           answer=sorted(ans), tokens_added=approx_tokens(ans))
                if pr is not None:
                    rec.update(score_probe(pr, ans)); rec["scored"] = True
                else:
                    rec["scored"] = False
            elif s.action == "teardown":
                a.teardown()
            f.write(json.dumps(rec) + "\n")
    print(f"wrote {path}")
    return path
