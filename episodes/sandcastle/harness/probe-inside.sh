#!/bin/bash
# Deterministic in-sandbox probes. Emits NDJSON (one object per probe), then a summary.
# Stdout/stderr are passed via temp files so a large result cannot blow ARG_MAX.
set +e
PY=python3

probe() {
  local name="$1"
  shift
  local outf errf code
  outf=$(mktemp)
  errf=$(mktemp)
  "$@" >"$outf" 2>"$errf"
  code=$?
  "$PY" - "$name" "$code" "$outf" "$errf" << 'PY'
import json, sys
name, code, outf, errf = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
stdout = open(outf, "r", errors="replace").read()[:8000]
stderr = open(errf, "r", errors="replace").read()[:4000]
print(json.dumps({"name": name, "exitCode": code, "stdout": stdout, "stderr": stderr}))
PY
  rm -f "$outf" "$errf"
}

echo '---PROBES---'
probe id id
probe whoami whoami
probe uname uname -s -m
probe capsh bash -lc 'command -v capsh >/dev/null && capsh --print || echo capsh-missing'
probe cap_eff bash -lc 'awk "/^CapEff|^CapPrm|^CapBnd|^NoNewPrivs/{print}" /proc/self/status'
probe sudo bash -lc 'command -v sudo; sudo -n true; echo sudo_exit=$?'
probe mknod bash -lc 'mknod /tmp/fakedev c 1 3; echo mknod_exit=$?; ls -l /tmp/fakedev 2>/dev/null; rm -f /tmp/fakedev'
probe mount_tmpfs bash -lc 'mkdir -p /tmp/mntprobe && mount -t tmpfs tmpfs /tmp/mntprobe; echo mount_exit=$?; umount /tmp/mntprobe 2>/dev/null; rmdir /tmp/mntprobe 2>/dev/null'
probe ping_loopback bash -lc 'ping -c 1 -W 2 localhost; echo ping_exit=$?'
probe pwd pwd
probe mountinfo bash -lc 'awk "/workspace|.git|overlay/{print}" /proc/self/mountinfo | head -n 40'
probe ls_home bash -lc 'echo /home; ls -la /home; echo /home/agent; ls -la /home/agent 2>&1 | head; echo /home/user; ls -la /home/user 2>&1 | head'
probe read_host_ssh bash -lc 'ls /home/user/.ssh 2>&1; head -c 80 /home/user/.ssh/id_ed25519 2>&1'
probe read_sibling_rel bash -lc 'echo trying=../sibling-canary.txt; cat ../sibling-canary.txt; echo exit=$?'
probe read_sibling_abs bash -lc 'echo trying_host_sibling_path; if [ -z "${HOST_SIBLING_PATH:-}" ]; then echo HOST_SIBLING_PATH_unset; else cat "$HOST_SIBLING_PATH"; echo exit=$?; fi'
probe read_host_tmp_canary cat /tmp/sandcastle-canary.txt
probe read_untracked_canary bash -lc 'cat secret-untracked-canary.txt 2>&1; find . -name secret-untracked-canary.txt 2>/dev/null'
probe write_etc_hosts bash -lc 'echo probe >> /etc/hosts; echo write_etc_exit=$?'
probe write_host_home bash -lc 'echo probe > /home/user/sandcastle-probe-write.txt; echo write_host_home_exit=$?'
probe write_container_tmp bash -lc 'echo probe > /tmp/sandcastle-sandbox-write.txt; echo write_tmp_exit=$?; ls -l /tmp/sandcastle-sandbox-write.txt'
probe write_dotdot bash -lc 'echo probe > ../outside-from-sandbox.txt; echo write_dotdot_exit=$?; ls -l ../outside-from-sandbox.txt 2>&1'
probe git_status bash -lc 'git status -sb; echo GITDIR=$(git rev-parse --git-dir); echo COMMON=$(git rev-parse --git-common-dir)'
probe write_git_config bash -lc 'git config --local user.evil true; echo git_config_exit=$?; git config --local --get user.evil; git config --local --list | tail'
probe write_git_hooks bash -lc 'echo eviltouch > .git/hooks/pre-commit; echo hook_exit=$?; ls -la .git/hooks 2>&1 | head'
probe write_git_pointer bash -lc 'echo eviltouch >> .git; echo git_pointer_exit=$?; ls -ld .git; ls -la .git 2>&1 | head'
probe mv_git bash -lc 'mv .git .git.bak; echo mv_git_exit=$?'
probe egress_example bash -lc 'curl -sS -m 8 -o /tmp/ex.body -w "http=%{http_code}\n" https://example.com; head -c 200 /tmp/ex.body'
probe egress_cloudflare bash -lc 'curl -sS -m 8 -o /dev/null -w "http=%{http_code}\n" https://www.cloudflare.com'
probe localhost_llm bash -lc 'if curl -fsS -m 3 http://localhost:18765/v1/models >/dev/null; then echo localhost_llm=reached; else echo localhost_llm=unreachable; fi'
probe gateway_llm bash -lc 'gw=${LLM_GATEWAY:-}; if [ -z "$gw" ]; then echo gateway_llm=skipped; elif curl -fsS -m 5 "http://${gw}:18765/v1/models" >/dev/null; then echo gateway_llm=reached; else echo gateway_llm=unreachable; fi'
probe dns_example bash -lc 'if getent hosts example.com >/dev/null; then echo dns=resolved; else echo dns=failed; fi'
echo '---END---'
