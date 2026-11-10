#!/bin/bash
# Part 2 (runs run-toolloop.sh twice at ctx 262144): extra seeds at max_tokens 2048 (seed 0 = determinism re-check),
# then max_tokens 8192 sensitivity for seeds 0 and 1. Same required env as run-toolloop.sh.
HERE=$(cd "$(dirname "$0")" && pwd); BASE=${OUT_BASE:-$PWD}
CTXS=262144 SEEDS="0 3 4 5 6 7 8 9" MAXT=2048 TAG= OUT_DIR=$BASE/runs-extra bash "$HERE/run-toolloop.sh"
CTXS=262144 SEEDS="0 1" MAXT=8192 TAG=-mt8192 OUT_DIR=$BASE/runs-mt8192 bash "$HERE/run-toolloop.sh"
