# Leak check: Qwen Code prompt-trim kit

Scope: every file in this folder and every file and directory name. Checked on 2026-11-10 (UTC+8) before handoff for publication.
The search terms are described by category, not listed literally.

**Verdict: PASS.** No secrets, credentials, private host or network identifiers, personal data, internal agent or message IDs, or private absolute paths.

## Tools and patterns

- A case-insensitive `grep -rnIiE` over contents, plus a `find` over relative names, for:
  - the test hosts' machine names and short host IDs;
  - the owner's local username, home paths, `$HOME` and `/home/`;
  - internal workspace and bench tree names, the internal harness name and paths, the host memory-slice name, internal container, service and launcher names;
  - tailnet, Tailscale and `.ts.net` names;
  - private IPv4 ranges (10/8, 172.16/12, 192.168/16, 100.64/10);
  - e-mail addresses;
  - token prefixes (GitHub, `sk-`, `hf_`, Slack `xox*`, AWS `AKIA`) and private-key blocks;
  - 1Password, `op://` and vault references;
  - password, secret, api_key, token=, bearer, authorization and cookie;
  - `.env` and SSH/key-file names;
  - UUIDs, internal chat and turn IDs, internal agent and bot names, inbox and Slack references, and canaries.
- A separate pass for hex strings of 32 or more characters and base64-like strings of 40 or more characters.
- A UTF-8 decode of every file, plus a check for symlinks and exec bits.
- A reproducibility check:
  - `scripts/analyze_runs.py`, run on the original data, reproduces `results/per-run-and-level.json` byte for byte;
  - `scripts/pooled.py` reproduces every pooled figure in RESULTS.md.

## Remaining matches (reviewed, all public or benign)

- `LOCAL_VLLM_API_KEY` in `config/qwen-settings.json.tmpl`: the name of an environment variable Qwen Code reads. There is no value. A local vLLM needs no real key.
- "secrets, API keys", "Slack, email, GitHub" and similar in `prompts/t4-p100.md` and `t4-p60.md`: instruction text from Qwen Code's own built-in prompt.
- "DSpark" and "spark-vllm-b12x": the public names of the speculative decoder and the vLLM image, as already in the public report.
- `github.com/maruthiprithivi/the-local-node`: the public repository link.
- Removed while packing: an unattributed model-repo revision hash in `config/matrix.yaml`. It was not needed to reproduce the run and could not be tied to a public repo name.

## Files included

- `RESULTS.md` is the already-public write-up. Only the title changed, and the "raw data kept private" line now points to the published files.
- `README.md` and `METHOD.md` are new docs. Every number in them comes from the public report.
- `prompts/*.md` (4 files) are verbatim from the run. p100 is Qwen Code 0.26.1's built-in prompt (Apache-2.0). The others are cuts of it.
- `scripts/analyze_runs.py` is verbatim from the run except the docstring, where the internal test and harness names were removed.
- `scripts/pooled.py` was written while packing (see METHOD.md) and verified against the original logs.
- `scripts/qwen_trim_adapter.py` is the adapter class verbatim from the run. A docstring documents the base Qwen Code command, and the internal module import was dropped (it is a reference excerpt).
- `config/qwen-settings.json.tmpl` is verbatim from the harness's template. It has no values beyond the model placeholder, a loopback base URL and sampling.
- `config/matrix.yaml` is the run matrix with these edits:
  - internal absolute prompt paths became `prompts/...`;
  - internal serve-script, startup-log and container-name fields were removed;
  - the unattributed model revision hash was removed;
  - internal throughput annotations were removed.
  - The settings that define the experiment are unchanged.
- `results/per-run-and-level.json` and `results/pooled-requests.json` hold aggregates only: no prompts, outputs or paths.

## Files excluded and why

- Per-run artifacts:
  - raw request logs (`requests.jsonl`), which hold full prompts, model outputs, task file contents and sandbox paths;
  - `proxy_state.json`;
  - agent diffs (`diff.patch` and `diff.stat`);
  - `score.txt` and `run.json`, whose per-run values are in the aggregates.
- The results database (SQLite), the resolved matrix (internal paths), `STATUS.log`, the progress log, the memory CSV (host cgroup and container IDs) and the suite launcher script (which has internal paths, service names and checks for internal containers).
- The private report (`t4-prompt-trim.md`). It has the host name, internal paths, service and unit names, and the image digest.
- The everyday task suite (task repos and hidden tests) and the benchmark harness. These are unpublished. Publishing the hidden tests would also retire those tasks as held-out tests, so that is a separate decision for the owner.
