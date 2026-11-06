#!/bin/sh
# Adaptation A6 (mode a only; run at image build time as root, see docker/Dockerfile.superagent).
# The linked prototype bundle resolved its peer @deepseek-ai/dsh-scope from its OWN dev install (a different
# prerelease) - a second module instance whose scope-parent map the host dsh never fills. Effect: the worker
# Session got only the orchestrator_* tools + subagent, and no bash/read/write. Fix: point that one peer at the
# copy inside the installed dsh package, so host and bundle share a single module instance.
# usage: A6-dsh-scope-peer.sh <prototype dir, e.g. /opt/dsh-superagent>
set -e
P=${1:?prototype dir}
H="$(npm root -g)/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-scope"
test -f "$H/package.json" || { echo "installed dsh has no nested dsh-scope at $H; check where your dsh resolves it" >&2; exit 1; }
rm -rf "$P/node_modules/@deepseek-ai/dsh-scope"
ln -s "$H" "$P/node_modules/@deepseek-ai/dsh-scope"
grep '"version"' "$P/node_modules/@deepseek-ai/dsh-scope/package.json"
