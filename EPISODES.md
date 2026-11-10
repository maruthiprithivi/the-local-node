# Episodes

Follow-along kits live in `episodes/`. Open a folder and run it from a clean checkout. The [playbook](PLAYBOOK.md) is the standard way to reproduce an episode demo end to end.

- [`episodes/01-kv-cache/`](episodes/01-kv-cache/) is the follow-along kit for episode one. It sizes a model's KV cache, measures that cache on Ollama, and renders the chart.
- [`episodes/02-super-agent/`](episodes/02-super-agent/) is the reproduction kit for comparing DeepSeek's Super-agent prototype with a single agent session on the same five bug fixes.
- [`episodes/03-lfm3-tool-loop/`](episodes/03-lfm3-tool-loop/) is the reproduction kit for testing how many chained tool calls LiquidAI LFM3-1.7B gets right with ~3K-token tool results, plus its decode-speed numbers.
- [`episodes/04-prompt-trim/`](episodes/04-prompt-trim/) is the reproduction kit for trimming Qwen Code's system prompt on a local Qwen3.8-27B: the prompt levels, settings, analysis scripts and results.
- [`episodes/05-prefix-reuse/`](episodes/05-prefix-reuse/) is the reproduction kit for a raw-text prefix-reuse timing and cache microbenchmark on vLLM, SGLang and Ollama.
