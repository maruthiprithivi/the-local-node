#!/usr/bin/env bash
# Lesson 14 — free the GPU (runs on the Spark). Downloads stay in ~/.cache/huggingface.
docker rm -f vllm sglang 2>/dev/null; docker ps; nvidia-smi --query-gpu=memory.used --format=csv
