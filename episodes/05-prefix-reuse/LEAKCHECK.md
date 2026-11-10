# Leak check: prefix-reuse kit

Scope: every file in this folder and every file and directory name. Checked on 2026-11-10 (UTC+8) before handoff for publication.
The search terms are described by category, not listed literally, so this file does not reintroduce them.

**Verdict: PASS.** No secrets, credentials, private host or network identifiers, personal data, internal agent or message IDs, or private absolute paths.

## Tools and patterns

- A case-insensitive `grep -rnIiE` over contents and a `find` over names (relative paths) for:
  - the test hosts' machine names and short host IDs;
  - the owner's local username and home paths, plus `$HOME` and `/home/` paths;
  - internal workspace and bench tree names, internal harness and suite names, the host memory-slice name, internal container names and internal job and launcher names;
  - tailnet, Tailscale and `.ts.net` names;
  - private IPv4 ranges (10/8, 172.16/12, 192.168/16, 100.64/10);
  - e-mail addresses;
  - token prefixes (GitHub, OpenAI-style `sk-`, Hugging Face `hf_`, Slack `xox*`, AWS `AKIA`) and `BEGIN … PRIVATE KEY`;
  - 1Password, `op://` and vault references;
  - `password`, `secret`, `api_key`, `token=`, `bearer`, `authorization` and `cookie`;
  - `.env`, SSH and key-file names;
  - UUIDs, internal chat and turn IDs, internal agent and bot names, inbox and Slack references, and canary markers.
- A separate pass for hex strings of 32 or more characters and base64-like strings of 40 or more characters.
- A UTF-8 decode of every file to catch binaries. A check for symlinks.
- A syntax check of `prefix_probe.py`, `analyze_prefix.py` and the three launch scripts, plus a JSON parse of the three published summaries. The GPU probe itself was not re-run here (it needs the model, an isolated server and an already-audited host watchdog).

## Remaining matches (reviewed, all public or benign)

- `github.com/maruthiprithivi/the-local-node`: the public repository link.
- `127.0.0.1`: loopback bind addresses in the probe and launch scripts.
- `/models` and `/absolute/path/to/...` placeholders in the README and launch scripts: container mount points and example environment values, not real host paths.
- The host watchdog unit names and cgroup parent (`bench.slice`, `bench-memguard`, `earlyoom`) and the container names (`bench-prefix-vllm2`, `bench-prefix-sglang`, `bench-prefix-ollama-q8`): these are the exact preconditions and names the original launch scripts check and use. They are a portability requirement, not a private network or machine identifier.
- `eugr/spark-vllm-b12x@sha256:…`, `lmsysorg/sglang@sha256:…` and `ollama/ollama@sha256:…`: public image pins used in the original run.
- Long hex strings: only the public sha256 values of the NVFP4 model files, the official Q8_0 GGUF, and the three image digests.
- Exec bits are set on the three `launch-*.sh` scripts on purpose.

## Files included

- `README.md` was rewritten into a follow-along how-to (inventory, headlines, how to read the published summaries, how to relaunch and probe, preconditions, limits). Measured numbers are unchanged from `report.md`.
- `METHOD.md`: path and wording fixes only (`analyze_prefix.py` instead of a leftover `public/` path; dropped internal recovery/backend phrasing). Method and figures are unchanged.
- `report.md`: typography (missing spaces) and a closing paragraph that no longer says the files were only prepared locally. Tables and measured numbers are unchanged.
- `runtime-compatibility.md`: removed an internal process note. Compatibility findings are unchanged.
- `prefix_probe.py`, `analyze_prefix.py`, `launch-*.sh`, `nvfp4-model-sha256.txt`, and the three `*-summary.json` files: verbatim from the original public pack, plus exec bits on the launch scripts.

## Files excluded and why

- Raw per-pair JSONL (timestamps, full server responses, reset bodies): not required to read the published summaries; held out as raw logs.
- Unpublished recovery and diagnostic evidence (the early rejected SGLang flush, unprimed Ollama pairs, host watchdog configuration, and any launcher or host logs). Those are described in `report.md` and `METHOD.md` but are not in this folder.
- Model weights and tokenizers. This kit does not bundle them.
