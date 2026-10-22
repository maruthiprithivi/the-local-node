# Playbook

This is the standard way to reproduce a Local Node episode demo from a clean checkout through a live measurement and a recording frame. Episode 1 (`episodes/01-kv-cache`) is the worked example. Follow the same order for later episodes: where the files live, setup, remote access, pre-flight, the live run, then the recording frame.

The repository is public. Commands below use placeholders (`<mac-host>`, `<linux-gpu-host>`, `<user>`, `<repo-url>`, `<public-key>`). Substitute your own values locally. Do not commit them.

## 1. Where things live

Three places, and two machine types.

| Place | What it is |
| --- | --- |
| This repo | One folder per episode under `episodes/`. Episode 1 is `episodes/01-kv-cache`: calculator, Ollama sweep, chart, whiteboard. `tracks/` is the course sequence. `website/` is the course site source. |
| [thelocalnode.dev](https://thelocalnode.dev) | The course site. The repo is the runnable companion. |
| Apple Silicon Mac | Reference machine: M2 Max, 64 GB, running Ollama. Unified memory. There is no separate GPU counter. |
| NVIDIA GB10 Linux box | Reference machine: Linux with an NVIDIA GPU, running Ollama. GPU memory comes from `nvidia-smi`. |

Call the machines `<mac-host>` and `<linux-gpu-host>` in notes, SSH config, and pull requests.

## 2. Setup

On both machines:

- Python 3.11 or newer. If `python` is missing, use `python3` in every command below.
- Node.js 22 or newer, for the chart only. The calculator and the sweep do not need it.
- [Ollama](https://ollama.com) installed, with `ollama serve` already running (on the Mac, the Ollama app is enough).
- Git.

Clone to a demos folder. `~/demos/the-local-node` is a suggestion, not a required path.

```bash
mkdir -p ~/demos
git clone <repo-url> ~/demos/the-local-node
cd ~/demos/the-local-node
```

Pull the small default model once. Nothing in the repo downloads a model unless you pass `--pull`.

```bash
ollama pull llama3.2:1b
```

A name that looks like 7B or larger stays refused until the sweep is run with `--pull`.

## 3. Remote access

Use a private mesh VPN such as Tailscale so both machines have stable names, then SSH with key authentication. Do not put the tailnet name, the hostnames, or the key in the repo.

Create a key and install the public line in `authorized_keys` on each machine:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519
```

```text
ssh-ed25519 <public-key> <comment>
```

Connect:

```bash
ssh <user>@<mac-host>
ssh <user>@<linux-gpu-host>
```

Run a sweep headless from your local terminal. The output files stay on that machine, under the episode `runs/` directory, which is gitignored.

```bash
ssh <user>@<linux-gpu-host> 'cd ~/demos/the-local-node/episodes/01-kv-cache && python3 measure_kv.py'
ssh <user>@<mac-host> 'cd ~/demos/the-local-node/episodes/01-kv-cache && python3 measure_kv.py'
```

Copy a finished JSON back only when you need it for the chart. Do not commit `runs/`.

```bash
scp <user>@<linux-gpu-host>:~/demos/the-local-node/episodes/01-kv-cache/runs/kv-sweep.json .
```

## 4. Pre-flight and smoke tests

From `episodes/01-kv-cache`. These checks do not start a long sweep and do not download a model.

```bash
python -m unittest discover -s tests -t . -v
pytest tests -q
cd chart && npm test
```

CI runs the unittest command. `pytest tests -q` runs the same files when pytest is installed. `npm test` checks that predicted growth and measured growth share one baseline. From the episode folder again, the calculator smoke test should print 4 GiB for the teaching shape and 1 GiB when 8 KV heads share the 32 attention heads:

```bash
python kv_cache.py --example
```

Ollama is reachable when this returns a model list:

```bash
curl -fsS http://localhost:11434/api/tags
ollama list
```

On Linux, confirm the GPU tool before trusting a sweep:

```bash
nvidia-smi --query-gpu=memory.used --format=csv,noheader
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits
```

If `memory.used` prints `[N/A]`, the sweep uses the compute-apps list for the runner that is serving the model. A missing `nvidia-smi` leaves the GPU column empty and the sweep still finishes. The Mac does not run this check.

`gpu_attribution` on each row says where the GPU number came from:

| Value | Meaning |
| --- | --- |
| `ollama-pid` | The PID Ollama reported for this model. |
| `new-pid` | A runner PID that appeared after the load. |
| `only-runner` | The only runner still resident. |
| `memory.used` | `nvidia-smi` reported a numeric device total. |
| `unattributed` | Several runners were resident and none could be tied to this model. Their memory is not summed. |
| `unavailable` | No separate GPU counter. macOS rows use this. Read `process_rss_bytes` instead. |

## 5. Running the live demo

Work in `episodes/01-kv-cache`.

Calculator, then a model you have installed:

```bash
python kv_cache.py --example
python kv_cache.py --ollama llama3.2:1b
```

Sweep. Other resident models are unloaded first so an older runner is not inside every GPU row. `--keep-others` leaves them loaded. `--pull` is the only way the script downloads.

```bash
python measure_kv.py
python measure_kv.py --pull
python measure_kv.py --model llama3.2:1b --contexts 512,1024,2048,4096,8192
python measure_kv.py --keep-others
```

`--out` is a prefix. `runs/kv-sweep-qwen3.8` writes `runs/kv-sweep-qwen3.8.json` and `runs/kv-sweep-qwen3.8.csv`.

Read the JSON and CSV before rendering. `predicted_kv_bytes` is the formula. `measured_runtime_bytes` is Ollama's reported size (weights, compute buffers, and cache). On Linux, compare `gpu_memory_bytes` from the shortest context to the longest. On macOS, compare `process_rss_bytes` the same way. The header line looks like `llama3.2:1b | layers: 16 | attention heads: 32 | KV heads: 8 | head dim 64`. A hybrid model prints `blocks: 65, KV layers: 16` as one segment.

Chart, from `chart/`. The frame is 1920x1080 at 24 fps. The bottom 150 px stays empty. A sample file renders before any live run. Pass a sweep JSON after a real run.

```bash
cd chart
npm install
npx remotion browser ensure
npm run render
npm run still
npm run render -- --props=../runs/kv-sweep.json
```

`npm run render` writes `chart/out/kv-cache.mp4`. `npm run still` writes one frame. Both series on a live file are growth from the same baseline context. Labels use GB (the math is GiB): `+2.0 GB predicted` and `+2.3 GB measured`. The shortest rung says `baseline`. The axis title is `extra memory used (GB)`. The formula line shows the total predicted cache at the longest context.

Whiteboard: open `whiteboard/kv-cache.excalidraw` in [Excalidraw](https://excalidraw.com). Strokes are black on white.

## 6. On-screen recording setup

Record in a 1920x1080 window so the capture matches the chart.

- **Orca** is the agent development environment. Open the episode folder, use a dark theme, and keep the window at 1920x1080. Close panels that show environment values, tokens, or local paths.
- **iTerm2** is the terminal. Use one clean profile: dark theme, a large font, and notifications off. Size the window to 1920x1080.
- Set a prompt that shows the folder and hides the user and the host:

```bash
export PS1='\W $ '
```

- Do not `echo` secrets, API keys, or environment values. Do not leave `OLLAMA_HOST` expanded on screen if it contains a host. Prefer `localhost` when Ollama is on the machine you are recording.
- Start the recording on the episode folder, after the pre-flight commands have already passed.

## 7. Known gotchas

These are fixes already in the episode 1 kit. Check them before treating a surprising number as a new bug.

- **Thinking-model TTFT.** Time to first token is the first thinking token or the first response token, whichever arrives first. The request sends `think: false` and retries without that field on HTTP 400 or 422. The token budget is 64, then 256 if the first reply stops on length before any token.
- **Hybrid models.** `full_attention_interval` means only some layers store a growing KV cache (interval 4 keeps one layer in four). A recurrent-layer list or `layer_types` overrides the interval. The formula multiplies the KV-layer count. The report prints both counts, for example `blocks: 65, KV layers: 16`. Sliding-attention layers still count. The formula uses the full context you pass, which is larger than a short window.
- **Ollama's reported size is a stepped estimate.** `measured_runtime_bytes` includes weights and compute buffers and moves in steps. Use GPU growth, or process RSS growth on macOS, from the shortest context. The chart plots that growth for both the prediction and the measurement.
- **Standalone `llama-server` on macOS.** RSS includes the Ollama server and runners whose parent chain reaches Ollama. A `llama-server` with no Ollama ancestor is left out. The Ollama app window is left out. Linux RSS is omitted because CUDA memory is not in the resident set.
- **GPU memory per model on the GB10.** `memory.used` can be `[N/A]`. The sweep then sums compute-apps only for the runner serving the swept model: the PID Ollama reports, else the new PID after the load, else the only remaining runner. Several older runners are not added together. Other models are unloaded before the sweep. `--keep-others` leaves them loaded. The file-level note counts rows that actually received a GPU figure.

## 8. For agents

Read this playbook before changing an episode demo.

- Run the tests in section 4, then a real sweep on the machine the change is about, before claiming the demo works. A green unit test does not replace a live Ollama run.
- Record every fix in the pull request description and, when it is a recurring trap, add it to section 7.
- Never commit secrets, hostnames, usernames, tailnet names, key material, or private local paths. Placeholders stay in the repo. `runs/` stays untracked.
- Open a pull request. Do not push to `main`.
- Publishing anything is a human decision. Stop after the pull request.
