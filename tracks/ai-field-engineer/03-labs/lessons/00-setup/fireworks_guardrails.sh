#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 00 · step 3 — Fireworks, with the handbrake on.
#
# The whole course costs well under $15 on Fireworks IF you follow one rule:
#
#     Serverless is pay-per-token (cents). Dedicated deployments bill per GPU-hour
#     from the moment they start, whether or not you send a request.
#
# Lessons 10 and 13 create deployments. They end with teardown. This script is
# the "is anything still running?" check — run it at the end of every session.
#
# Commands follow the firectl docs at time of writing; if a flag has moved,
# `firectl <command> --help` is the source of truth.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

if ! command -v firectl >/dev/null; then
  cat <<'EOF'
firectl is not installed. On a Mac:
    brew tap fw-ai/firectl && brew install firectl
    firectl signin
(or see https://docs.fireworks.ai/tools-sdks/firectl/firectl)
EOF
  exit 1
fi

echo "▸ Who am I?"
firectl whoami || { echo "Run: firectl signin"; exit 1; }

echo
echo "▸ Deployments (anything listed here is billing by the hour):"
firectl deployment list

echo
echo "▸ Fine-tuning jobs (a running job bills training tokens):"
firectl sftj list 2>/dev/null || true

cat <<'EOF'

Checklist
  [ ] A monthly budget / spend alert is set in the console (Billing → usage limits).
  [ ] The deployments list above is empty, unless you are mid-lesson.
  [ ] Your key is in .env, not in any file you commit.

To delete a leftover deployment:   firectl deployment delete <DEPLOYMENT_ID>
EOF
