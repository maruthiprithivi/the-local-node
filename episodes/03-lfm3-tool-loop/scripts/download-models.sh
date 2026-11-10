#!/bin/bash
# Official LiquidAI/LFM3-1.7B-GGUF files, checked against the sha256 in the Hugging Face LFS metadata.
# Usage: MODEL_DIR=/path/to/models/LFM3-1.7B-GGUF bash download-models.sh
set -u; : "${MODEL_DIR:?set MODEL_DIR}"; mkdir -p "$MODEL_DIR"; cd "$MODEL_DIR"
for x in "LFM3-1.7B-Q4_K_M.gguf 3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4" "LFM3-1.7B-Q8_0.gguf 8f6b24182258205e9e01e21f1f24a1f208c1e8115578825d202ce39976af20b6" "LFM3-1.7B-BF16.gguf 39158a79f56edb85e0c4252ce6447b8d7883ef82ffedd02f0cda7c84da5e9f68"; do
  set -- $x; curl -sfL -C - -o $1 https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF/resolve/main/$1
  echo "$2  $1" | sha256sum -c || echo "SHA FAIL $1"
done
curl -sfL https://huggingface.co/api/models/LiquidAI/LFM3-1.7B-GGUF | python3 -c "import json,sys;print(\"repo sha\",json.load(sys.stdin)[\"sha\"])"
