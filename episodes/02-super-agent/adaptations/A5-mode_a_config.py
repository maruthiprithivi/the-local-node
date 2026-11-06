#!/usr/bin/env python3
"""Mode a, inside the sandbox: save dsh-superagent settings through its documented Management API, in SETUP.md
order: github Source -> policy allowed list -> executor prepare command. Waits for restarts; prints a JSON summary.

Adaptation A5 lives in PREPARE: the documented example fetches from https://github.com/$DSH_SUPERAGENT_GITHUB_REPOSITORY.git;
here it fetches from the local forge URL instead. Everything else is the documented example."""
import json, os, time, urllib.request, urllib.error
U = "http://127.0.0.1:3082/orchestrator/api/"
HOME = os.environ.get("HOME", "/home/agent")
FORGE_URL = os.environ.get("FORGE_URL", "http://127.0.0.1:3000")
REPO = os.environ.get("FORGE_REPO", "maint/widgets")
OWNER = REPO.split("/")[0]
def api(method, path, data=None):
    r = urllib.request.Request(U + path, method=method, data=json.dumps(data).encode() if data is not None else None)
    r.add_header("x-orchestrator-request", "1"); r.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp: return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"null")
    except Exception as e: return 0, str(e)
def wait_up(t=180):
    t0 = time.time()
    while time.time() - t0 < t:
        c, s = api("GET", "state")
        if c == 200 and s.get("health", {}).get("runtime", {}).get("state") in ("ready", "paused"): return s
        time.sleep(2)
    raise SystemExit("service did not come back")
CLONE = f"{HOME}/src/widgets"
PREPARE = (f'git -C {CLONE} fetch --no-tags "{FORGE_URL}/$DSH_SUPERAGENT_GITHUB_REPOSITORY.git" '   # A5: forge URL, not github.com
           '"${DSH_SUPERAGENT_GITHUB_PR_HEAD:-HEAD}:refs/dsh-superagent/$DSH_SUPERAGENT_TICKET" && '
           f'git -C {CLONE} worktree add -b "agent/$DSH_SUPERAGENT_NAME" "$DSH_SUPERAGENT_DIR" "refs/dsh-superagent/$DSH_SUPERAGENT_TICKET"')
out = {}
wait_up()
c, st = api("GET", "settings")
src = next(s for s in st["sources"] if s["id"] == "github")
cfg = dict(src["value"]["config"]); cfg.update({"repository": REPO, "cli": f"{HOME}/.local/bin/gh-agent"})   # A2: shim as Agent GitHub CLI
out["github"] = api("PUT", "settings/source:github", {"value": {"enabled": True, "config": cfg}, "revision": src["revision"]})
time.sleep(3); wait_up()
c, st = api("GET", "settings")
pol = st["blocks"]["policy"]
pv = dict(pol["value"]); pv["sources"] = {"github": {"allowed": [{"id": OWNER}]}}
out["policy"] = api("PUT", "settings/policy", {"value": pv, "revision": pol["revision"]})
time.sleep(2); wait_up()
c, st = api("GET", "settings")
ex = st["blocks"]["executor"]
ev = dict(ex["value"]); ev["prepare"] = PREPARE
out["executor"] = api("PUT", "settings/executor", {"value": ev, "revision": ex["revision"]})
time.sleep(2); s = wait_up()
out["state"] = {"setup_problem": s.get("setup", {}).get("problem"), "accounts": s.get("setup", {}).get("accounts"),
                "health": {k: v.get("state") for k, v in s.get("health", {}).items()}, "load": s.get("load")}
print(json.dumps(out, indent=1))
