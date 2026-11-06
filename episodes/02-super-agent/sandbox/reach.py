#!/usr/bin/env python3
"""Reach check: what can the agent touch from inside the sandbox? Benign probes only; writes JSON to stdout.

Run INSIDE the agent sandbox as the agent user, with the mode-a worker's environment (host/run_matrix.py reach does
this: PATH with the worker-bin shims, GIT_CONFIG_GLOBAL = worker gitconfig). Uses the agent's own forge credentials.
The token is read from the agent's token file and is NEVER printed; response bodies are cut short and redacted.

WARNING: the git probes push an empty commit to `main` and force-push it back, and the late probes try to delete
`main` and the repo. Run it only against the throwaway forge; the runner resets the repo afterwards.

Env (defaults): SANDBOX_HOST_ALIAS (host.openshell.internal, OpenShell's generic alias for the sandbox host),
MODEL_HOST_PORT (8000), FORGE_HOST_PORT (13300), OTHER_MODEL_PORT (11434, another local model server port that must
stay unreachable), HOST_HOME_PROBES (colon-separated host paths that must NOT be visible, e.g. /home/hostuser),
MODEL_WEIGHTS_PROBES (colon-separated model weight dirs that must NOT be visible, default /models).
"""
import base64, json, os, re, secrets, socket, subprocess, urllib.request, urllib.error
H = os.path.expanduser("~")
HOST = os.environ.get("SANDBOX_HOST_ALIAS", "host.openshell.internal")
MP = int(os.environ.get("MODEL_HOST_PORT", "8000")); FP = int(os.environ.get("FORGE_HOST_PORT", "13300"))
OTHER = int(os.environ.get("OTHER_MODEL_PORT", "11434"))
HOST_HOMES = [p for p in os.environ.get("HOST_HOME_PROBES", "/home/hostuser:/home/hostuser/bench").split(":") if p]
WEIGHTS = [p for p in os.environ.get("MODEL_WEIGHTS_PROBES", "/models").split(":") if p]
FWD = "/opt/kit-bin/kit-fwd"
R = {"id": subprocess.run(["id"], capture_output=True, text=True).stdout.strip(), "files": {}, "net": {}, "forge": {}, "git": {}}
st = open("/proc/self/status").read()
R["proc"] = {k: v.strip() for k, v in (l.split(":", 1) for l in st.splitlines()) if k in ("CapEff", "CapPrm", "NoNewPrivs", "Seccomp", "Seccomp_filters")}
R["env_names"] = sorted(os.environ)          # names only, never values
def rd(p):
    try:
        if os.path.isdir(p): return "dir-listable:%d" % len(os.listdir(p))
        with open(p, "rb") as f: f.read(64); return "readable"
    except FileNotFoundError: return "absent"
    except PermissionError: return "denied"
    except OSError as e: return f"err:{e.errno}"
def wr(p):
    t = os.path.join(p, f".reach-{os.getpid()}") if os.path.isdir(p) else p + f".reach-{os.getpid()}"
    try:
        with open(t, "w") as f: f.write("x")
        os.unlink(t); return "writable"
    except FileNotFoundError: return "absent"
    except PermissionError: return "denied"
    except OSError as e: return f"err:{e.errno}"
for p in [H, f"{H}/.ssh/id_ed25519", f"{H}/.config/gh-agent/token", f"{H}/.config/gh-agent/config.json", f"{H}/src/widgets",
          f"{H}/.dsh/state/superagent/orchestrator.sqlite", f"{H}/.dsh/state/superagent/worker-gitconfig", f"{H}/dsh-superagent/.artifacts",
          "/work", "/tmp", "/var/tmp", "/dev/shm", "/etc", "/etc/passwd", "/etc/shadow", "/etc/hosts", "/opt/dsh-superagent", "/opt/ghcompat/gh",
          "/opt/kit-bin", "/usr/bin", "/root", "/proc/1/environ", "/sys/fs/cgroup", "/var/run/docker.sock", "/run/docker.sock",
          *HOST_HOMES, *WEIGHTS, "/mnt", "/media", "/srv", "/dev/pts", "/boot"]:
    R["files"][p] = {"read": rd(p), "write": wr(p) if os.path.exists(p) else "absent"}
def tcp(host, port, exe=None):
    code = f"import socket;s=socket.socket();s.settimeout(5);s.connect(({host!r},{port}));print('connected')"
    try:
        r = subprocess.run([exe or "python3", "-c", code], capture_output=True, text=True, timeout=12)
        return "connected" if "connected" in r.stdout else ("refused/denied: " + (r.stderr.strip().splitlines() or [""])[-1][:120])
    except subprocess.TimeoutExpired: return "timeout"
for name, (h, p, exe) in {
    "model via in-sandbox forwarder 127.0.0.1:8000 (expect connected)": ("127.0.0.1", 8000, None),
    "forge via in-sandbox forwarder 127.0.0.1:3000 (expect connected)": ("127.0.0.1", 3000, None),
    f"model direct {HOST}:{MP} (python3)": (HOST, MP, None),
    f"forge direct {HOST}:{FP} (python3)": (HOST, FP, None),
    f"host ssh {HOST}:22 (python3)": (HOST, 22, None),
    "internet 1.1.1.1:443 (python3)": ("1.1.1.1", 443, None),
    "github.com:443 (python3)": ("github.com", 443, None),
    "api.deepseek.com:443 (python3)": ("api.deepseek.com", 443, None),
    "cloud metadata 169.254.169.254:80": ("169.254.169.254", 80, None),
    "docker bridge 172.17.0.1:8000": ("172.17.0.1", 8000, None),
    f"forwarder binary -> {HOST}:{MP} (the allowed rule)": (HOST, MP, FWD),
    f"forwarder binary -> {HOST}:{FP} (the allowed rule)": (HOST, FP, FWD),
    f"forwarder binary -> {HOST}:22": (HOST, 22, FWD),
    "forwarder binary -> 1.1.1.1:443": ("1.1.1.1", 443, FWD),
    f"forwarder binary -> {HOST}:{OTHER} (another local model port)": (HOST, OTHER, FWD),
}.items():
    R["net"][name] = tcp(h, p, exe)
r = subprocess.run(["curl", "-s", "-m", "8", "-o", "/dev/null", "-w", "%{http_code}", "https://example.com"], capture_output=True, text=True)
R["net"]["curl https://example.com"] = f"rc={r.returncode} http={r.stdout}"
try: R["net"]["dns github.com"] = socket.gethostbyname("github.com")
except Exception as e: R["net"]["dns github.com"] = f"fail {e}"
# ---- forge token scope (Gitea API through the forwarder) ----
CFG = json.load(open(f"{H}/.config/gh-agent/config.json")); TOK = open(os.path.expanduser(CFG["token_file"])).read().strip()
API = CFG["base"] + "/api/v1"; ME = CFG.get("login", "agentbot")
def red(b):
    b = b.replace(TOK, "<token>") if TOK else b
    return re.sub(r'("(sha1|token_last_eight|access_token)"\s*:\s*")[^"]*', r'\1<redacted>', b)
def f(method, path, data=None):
    q = urllib.request.Request(API + path, method=method, data=json.dumps(data).encode() if data is not None else None)
    q.add_header("Authorization", f"token {TOK}"); q.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(q, timeout=30) as resp: return resp.status, red(resp.read()[:400].decode(errors="replace"))
    except urllib.error.HTTPError as e: return e.code, red(e.read()[:400].decode(errors="replace"))
fake_pub = "ssh-ed25519 " + base64.b64encode(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + secrets.token_bytes(32)).decode() + " reach"
checks = [  # (name, method, path, body)   expected in a scoped setup: 404 / 403 except the last four
    ("whoami GET /user", "GET", "/user", None),
    ("repos visible GET /user/repos", "GET", "/user/repos", None),
    ("search all repos GET /repos/search", "GET", "/repos/search?limit=50", None),
    ("read other private repo maint/private-notes (expect 404)", "GET", "/repos/maint/private-notes", None),
    ("read other user's private repo reporter/scratch (expect 404)", "GET", "/repos/reporter/scratch", None),
    ("issue in other repo maint/private-notes (expect 404)", "POST", "/repos/maint/private-notes/issues", {"title": "reach-check"}),
    ("create public repo POST /user/repos (expect 403)", "POST", "/user/repos", {"name": "reach-public", "private": False}),
    ("create org POST /orgs (expect 403)", "POST", "/orgs", {"username": "reach-org"}),
    ("admin list users (expect 403)", "GET", "/admin/users", None),
    ("admin create user (expect 403)", "POST", "/admin/users", {"username": "reachx", "email": "reachx@forge.invalid", "password": secrets.token_urlsafe(16)}),
    ("make repo public (expect 403)", "PATCH", "/repos/maint/widgets", {"private": False}),
    ("add collaborator (expect 403)", "PUT", "/repos/maint/widgets/collaborators/outsider", {"permission": "admin"}),
    ("create webhook (expect 403)", "POST", "/repos/maint/widgets/hooks", {"type": "gitea", "config": {"url": "http://127.0.0.1:9/", "content_type": "json"}, "active": True}),
    ("create deploy key (expect 403)", "POST", "/repos/maint/widgets/keys", {"title": "reach", "key": fake_pub, "read_only": False}),
    ("mint new token (expect 403)", "POST", f"/users/{ME}/tokens", {"name": "reach", "scopes": ["all"]}),
    ("list own tokens", "GET", f"/users/{ME}/tokens", None),
    ("create issue in maint/widgets (allowed: 201)", "POST", "/repos/maint/widgets/issues", {"title": "reach-check issue", "body": "benign reach probe"}),
    ("create branch reach-tmp (allowed: 201)", "POST", "/repos/maint/widgets/branches", {"new_branch_name": "reach-tmp", "old_branch_name": "main"}),
    ("delete branch reach-tmp (allowed: 204)", "DELETE", "/repos/maint/widgets/branches/reach-tmp", None),
]
late = [("delete default branch main (expect 403)", "DELETE", "/repos/maint/widgets/branches/main", None),
        ("delete repo (expect 403)", "DELETE", "/repos/maint/widgets", None)]
for name, m, p, d in checks:
    c, b = f(m, p, d); R["forge"][name] = {"status": c, "body": b[:160]}
try:
    q = urllib.request.Request(API + "/user/repos", headers={"Authorization": f"token {TOK}"})
    R["forge"]["visible_repo_names"] = [x["full_name"] for x in json.loads(urllib.request.urlopen(q, timeout=30).read())]
except Exception as e: R["forge"]["visible_repo_names"] = str(e)[:200]
# ---- the two gaps found on Nov 4 2026 ----
def sh(c):
    r = subprocess.run(["bash", "-lc", c], capture_output=True, text=True, timeout=120); return r.returncode, red((r.stdout + r.stderr)[-300:])
# 1) does `gh auth token` print the token? (output is discarded here; we only record yes/no)
R["git"]["gh auth token prints the token"] = sh("gh auth token 2>/dev/null | grep -q . && echo yes || echo no")[1].strip()
# 2) is main protected? push an empty commit straight to main, then force-push it away again
R["git"]["direct push to main"] = sh("set -e; rm -rf /tmp/rc && git clone -q http://127.0.0.1:3000/maint/widgets.git /tmp/rc && cd /tmp/rc && "
                                    f"git -c user.name={ME} -c user.email={ME}@forge.invalid commit -q --allow-empty -m reach-check && git push -q origin HEAD:main && echo PUSHED")
R["git"]["force push to main"] = sh("cd /tmp/rc && git reset -q --hard HEAD~1 && git push -q --force origin HEAD:main && echo FORCE_PUSHED")
for name, m, p, d in late:
    c, b = f(m, p, d); R["forge"][name] = {"status": c, "body": b[:160]}
print(json.dumps(R, indent=1))
