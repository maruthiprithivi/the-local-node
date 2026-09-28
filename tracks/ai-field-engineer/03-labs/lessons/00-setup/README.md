# 00 · Setup and guardrails

> **Lab book:** Local labs → **L1** · Guardrails panel  **Watch:** video 9 `09-serving-stack.mp4` (first half)
> **Time:** 15 min  **Cost:** free

## What and why

You are building a small inference lab on your Mac: three local servers, one shared
Python toolkit (`felab`) and a fake server for offline practice. You also set the
Fireworks handbrake *before* spending anything.

On a Mac, **RAM is your VRAM**. The GPU and CPU share one pool of memory, so the model
competes with your browser for space. **Memory bandwidth is your speed limit**, and
`check_env.py` prints both.

## Run

```bash
bash lessons/00-setup/setup_mac.sh          # installs ollama, llama.cpp, venv, felab
source .venv/bin/activate
python lessons/00-setup/check_env.py        # chip, RAM, bandwidth, which servers are up

# first real model (≈4.9 GB download)
ollama serve &                              # leave running
ollama pull llama3.1:8b
python lessons/00-setup/check_env.py        # ollama should now say UP ✓

# the offline mock (every lesson works against it)
python -m felab.mock_server &               # :9000

# Fireworks — only when you reach lesson 01b
bash lessons/00-setup/fireworks_guardrails.sh
```

## What you should see

```
memory      36.0 GB   ← model weights + KV cache must fit in ~70% of this
bandwidth   ~273 GB/s ← decode ceiling for an 8B model at 4-bit (≈4.9 GB): ~56 tok/s
mock       http://localhost:9000/v1     UP ✓
ollama     http://localhost:11434/v1    UP ✓
```

## Check yourself

1. Your Mac has 36 GB. Roughly the biggest 4-bit model you can run comfortably? *(≈ 0.7 × 36 ≈ 25 GB of weights, so about a 40B dense model at 4-bit, with little room left for context.)*
2. Why does the script print bandwidth rather than GPU cores? *(Decode reads every weight once per token, so bandwidth, not compute, sets the speed.)*

## Explain what you learned

> "On unified memory, model size competes with everything else on the box. I size to
> about 70% of RAM and check the bandwidth before I promise a tokens-per-second number."

**Next →** [01 · Latency harness](../01-latency-harness/)
