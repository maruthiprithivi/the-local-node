#!/usr/bin/env bash
# Lesson 14 · step 0 — what is this box? (runs on the Spark)
# DGX Spark = GB10 Grace-Blackwell, 128 GB unified memory at ~273 GB/s, arm64, CUDA.
# Rule: everything runs in CONTAINERS. Never `pip install vllm` on the host.
set -uo pipefail
echo "▸ GPU / driver / CUDA";   nvidia-smi --query-gpu=name,driver_version --format=csv,noheader; nvidia-smi | grep -i "cuda version"
echo "▸ memory";               free -g | head -2
echo "▸ arch";                 uname -m
echo "▸ docker + GPU access";  docker run --rm --gpus all ubuntu:24.04 nvidia-smi -L 2>&1 | tail -1
echo "▸ running containers";   docker ps --format '{{.Names}}  {{.Image}}  {{.Status}}'
