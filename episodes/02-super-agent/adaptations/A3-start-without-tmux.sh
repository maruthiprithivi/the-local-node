#!/bin/bash
# Adaptation A3 (mode a): tmux cannot allocate a pty inside the sandbox (Landlock does not allow /dev/pts and we
# did not widen the policy). So the exact command the prototype's service script would run in tmux is started with
# setsid/nohup instead; then `scripts/dsh-superagent start` adopts the running process (its "already running"
# branch) and does its normal health wait.
. "${KIT_IN:-/tmp/kit}/env.sh"
cd ~/dsh-superagent; mkdir -p .artifacts
LOG=$HOME/dsh-superagent/.artifacts/dsh-superagent-superagent-$(date +%Y%m%d-%H%M%S)-$$.log
( umask 077; setsid nohup "$(command -v dsh)" --profile superagent --no-open </dev/null >>"$LOG" 2>&1 & )
for i in $(seq 30); do pgrep -f -- "--profile superagent --no-open" >/dev/null && break; sleep 1; done
sleep 3
scripts/dsh-superagent start --timeout 120 2>&1 || scripts/dsh-superagent start 2>&1; echo "start rc=$?"
scripts/dsh-superagent status; echo "status rc=$?"
