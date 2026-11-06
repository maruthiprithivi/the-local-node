#!/bin/bash
# Mode b run: one headless dsh session, prompt from $KIT_IN/prompt-b.txt (written by host/run_matrix.py).
. "$(dirname "$0")/env.sh"
export DSH_SUPERAGENT_GITHUB_REPOSITORY=$FORGE_REPO GHCOMPAT_CONFIG=$HOME/.config/gh-agent/config.json
cd ~/src/widgets
dsh --profile headless --json - < "$KIT_IN/prompt-b.txt" > /tmp/run-b.jsonl 2> /tmp/run-b.stderr
echo "dsh_rc=$?"
