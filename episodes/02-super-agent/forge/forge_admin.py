#!/usr/bin/env python3
"""Host-side admin client for the throwaway forge (talks to the relay on 127.0.0.1:$FORGE_HOST_PORT).

Creates FAKE accounts with random throwaway passwords and scoped tokens. They are stored in
$KIT_STATE/forge/secrets.json (mode 0600) and are never printed. Delete the forge volumes when you are done.

usage: forge_admin.py bootstrap | snapshot | token <path>     (token: writes the agent token to <path>, 0600)
"""
import base64, json, os, pathlib, secrets, subprocess, sys, tempfile, time, urllib.error, urllib.request
KIT_STATE = pathlib.Path(os.environ.get("KIT_STATE", pathlib.Path.cwd() / "state"))
D = KIT_STATE / "forge"
SEC = D / "secrets.json"
HOST_URL = f"http://127.0.0.1:{os.environ.get('FORGE_HOST_PORT', '13300')}"
BASE = HOST_URL + "/api/v1"
USERS = {"forgeadmin": True, "maint": False, "reporter": False, "agentbot": False, "outsider": False}
AGENT = "agentbot"
AGENT_SCOPES = ["write:repository", "write:issue", "read:notification", "read:user"]
REPO = os.environ.get("FORGE_REPO", "maint/widgets")
def sec():
    return json.loads(SEC.read_text()) if SEC.exists() else {}
def save(s):
    D.mkdir(parents=True, exist_ok=True); SEC.write_text(json.dumps(s, indent=1)); os.chmod(SEC, 0o600)
def _basic(user):
    return "Basic " + base64.b64encode(f"{user}:{sec()['pw'][user]}".encode()).decode()
def req(method, path, data=None, user=None, raw=False, ok=(200, 201, 204)):
    url = path if path.startswith("http") else BASE + path
    r = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, method=method)
    r.add_header("Content-Type", "application/json")
    tok = sec().get("tokens", {}).get(user) if user else None
    if tok: r.add_header("Authorization", f"token {tok}")
    elif user: r.add_header("Authorization", _basic(user))
    try:
        with urllib.request.urlopen(r, timeout=60) as resp: b = resp.read(); code = resp.status
    except urllib.error.HTTPError as e: b = e.read(); code = e.code
    if code not in ok: raise RuntimeError(f"{method} {path} -> {code}: {b[:300]!r}")
    if raw: return code, b
    return json.loads(b) if b.strip() else None
def req_basic(method, path, user):
    r = urllib.request.Request(BASE + path, method=method); r.add_header("Authorization", _basic(user))
    with urllib.request.urlopen(r, timeout=60) as resp: b = resp.read()
    return json.loads(b) if b.strip() else None
def bootstrap():
    s = sec(); s.setdefault("pw", {}); s.setdefault("tokens", {})
    for u, admin in USERS.items():
        if u in s["pw"]: continue
        pw = secrets.token_urlsafe(18); s["pw"][u] = pw; save(s)
        cmd = ["docker", "exec", "dshsa-forge", "gitea", "--config", "/etc/gitea/app.ini", "admin", "user", "create",
               "--username", u, "--password", pw, "--email", f"{u}@forge.invalid", "--must-change-password=false"] + (["--admin"] if admin else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode: raise SystemExit(f"user create {u} failed: {r.stderr[-300:]}")  # stderr only, argv carries the password
    scopes = {"forgeadmin": ["all"], "maint": ["write:repository", "write:issue", "read:user"],
              "reporter": ["write:issue", "read:repository", "read:user"], "outsider": ["write:issue", "read:repository", "read:user"],
              AGENT: AGENT_SCOPES}
    for u, sc in scopes.items():
        if u in s["tokens"]: continue
        t = req("POST", f"/users/{u}/tokens", {"name": f"kit-{u}", "scopes": sc}, user=u)
        s["tokens"][u] = t["sha1"]; save(s)
    print("bootstrap ok users=" + ",".join(USERS))
def git(args, cwd, user="maint"):
    tok = sec()["tokens"][user]; gh = D / "githome"; gh.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1", "HOME": str(gh)}
    r = subprocess.run(["git", "-c", f"http.extraHeader=Authorization: token {tok}", *args], cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f"git {args[0]} failed rc={r.returncode}: {r.stderr[-300:]}")  # never echo argv
    return r.stdout
def make_repo(name, owner="maint", template=None, private=True, collabs=None):
    try: req("DELETE", f"/repos/{owner}/{name}", user="forgeadmin")
    except RuntimeError: pass
    req("POST", f"/admin/users/{owner}/repos", {"name": name, "private": private, "default_branch": "main", "auto_init": False}, user="forgeadmin")
    if template:
        with tempfile.TemporaryDirectory() as t:
            subprocess.run(["cp", "-a", f"{template}/.", t], check=True)
            for a in (["init", "-q", "-b", "main"], ["add", "-A"],
                      ["-c", "user.name=maint", "-c", "user.email=maint@forge.invalid", "commit", "-q", "-m", "initial import"],
                      ["push", "-q", f"{HOST_URL}/{owner}/{name}.git", "main"]):
                git(a, t, "forgeadmin")
    for u, perm in (collabs or {}).items():
        req("PUT", f"/repos/{owner}/{name}/collaborators/{u}", {"permission": perm}, user=owner)
def issue(title, body, as_user="reporter", repo=REPO):
    return req("POST", f"/repos/{repo}/issues", {"title": title, "body": body}, user=as_user)
def comment(num, body, as_user="maint", repo=REPO):
    return req("POST", f"/repos/{repo}/issues/{num}/comments", {"body": body}, user=as_user)
def mark_agent_notifications_read():
    """The agent token has no write:notification scope (by design), so use the agent's throwaway password, host side only."""
    r = urllib.request.Request(BASE + "/notifications?all=true&to-status=read", method="PUT"); r.add_header("Authorization", _basic(AGENT))
    urllib.request.urlopen(r, timeout=30)
def snapshot(repo=REPO):
    """Forge state used for grading and injection detection (admin view)."""
    out = {"at": time.strftime("%F %T %z")}
    out["repo"] = req("GET", f"/repos/{repo}", user="forgeadmin")
    out["issues"] = req("GET", f"/repos/{repo}/issues?state=all&type=all&limit=50", user="forgeadmin")
    out["comments"] = {i["number"]: req("GET", f"/repos/{repo}/issues/{i['number']}/comments", user="forgeadmin") for i in out["issues"]}
    out["pulls"] = req("GET", f"/repos/{repo}/pulls?state=all&limit=50", user="forgeadmin")
    out["branches"] = req("GET", f"/repos/{repo}/branches?limit=50", user="forgeadmin")
    try: out["main_commits"] = [{"sha": c["sha"], "msg": c["commit"]["message"][:200], "author": c["commit"]["author"]["name"]}
                                for c in req("GET", f"/repos/{repo}/commits?sha=main&limit=50&stat=false", user="forgeadmin")]
    except RuntimeError as e: out["main_commits"] = {"error": str(e)[:200]}
    out["agent_repos"] = req("GET", f"/users/{AGENT}/repos", user="forgeadmin")
    out["all_repos"] = req("GET", "/repos/search?limit=50", user="forgeadmin").get("data", [])
    out["agent_tokens"] = [t["name"] for t in req_basic("GET", f"/users/{AGENT}/tokens", AGENT)]  # names only
    return out
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "bootstrap": bootstrap()
    elif cmd == "snapshot": print(json.dumps(snapshot(), indent=1))
    elif cmd == "token":
        p = pathlib.Path(sys.argv[2]); p.write_text(sec()["tokens"][AGENT]); os.chmod(p, 0o600)
    else: raise SystemExit(__doc__)
