#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Lesson 00 · step 1 — install the local toolchain on an Apple-silicon Mac.
#
#   Ollama     convenience server (hides the flags)          → :11434
#   llama.cpp  the engine under Ollama, every flag exposed   → :8080
#   MLX        Apple's own array framework; fastest on M-series, can fine-tune
#
# Safe to re-run: each step checks before installing.
# Run from the repo root:   bash lessons/00-setup/setup_mac.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

say() { printf "\n\033[1;36m▸ %s\033[0m\n" "$*"; }

[[ "$(uname -s)" == "Darwin" ]] || { echo "This script is for macOS. On Linux use the Spark track (lesson 14)."; exit 1; }
[[ "$(uname -m)" == "arm64" ]]  || echo "⚠ Intel Mac detected: MLX will not work; Ollama/llama.cpp will be slow."

say "Homebrew"
command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }

say "Ollama + llama.cpp (Metal builds — no CUDA on a Mac)"
brew list ollama    >/dev/null 2>&1 || brew install ollama
brew list llama.cpp >/dev/null 2>&1 || brew install llama.cpp

say "Python venv with the repo's helper package (felab) + openai SDK + mlx-lm"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
pip install -q -e .            # makes `import felab` work from any lesson folder

say "A .env file for your settings (git-ignored)"
if [[ ! -f .env ]]; then cp .env.example .env; echo "  created .env — edit it later for Fireworks / Spark"; fi

say "Done. Next:"
cat <<'EOF'
  source .venv/bin/activate
  python lessons/00-setup/check_env.py
EOF
