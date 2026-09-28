#!/usr/bin/env bash
# Run any script in this folder ON the Spark, from your Mac:
#     bash remote.sh 0_check.sh
#     bash remote.sh 1_vllm.sh nvidia/Llama-3.1-8B-Instruct-FP8
# Needs SPARK_IP (and optionally SPARK_USER) in .env or the environment, and SSH keys set up.
set -euo pipefail
cd "$(dirname "$0")"
[[ -f ../../.env ]] && set -a && source ../../.env && set +a
: "${SPARK_IP:?set SPARK_IP in .env}"
script=$1; shift
ssh "${SPARK_USER:-nvidia}@$SPARK_IP" "HF_TOKEN=${HF_TOKEN:-} bash -s -- $*" < "$script"
