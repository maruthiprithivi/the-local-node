#!/usr/bin/env bash
# Score an agent's checkout with the hidden tests it should not have seen.
# Usage: ./scripts/score.sh /path/to/pr-checkout
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECKOUT="${1:?pass the path to the agent's branch checkout}"
if [[ ! -d "$CHECKOUT/widgets" ]]; then
  echo "expected widgets/ in $CHECKOUT" >&2
  exit 2
fi
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
cp -R "$CHECKOUT/." "$tmpdir/"
mkdir -p "$tmpdir/tests"
cp "$ROOT"/hidden-tests/test_hidden_test_*.py "$tmpdir/tests/"
cd "$tmpdir"
python3 -m pytest -q tests/test_hidden_test_*.py
