# Sandcastle 0.14.0, run locally

This folder is the evidence kit for a run of the **current public release** of Matt Pocock's Sandcastle: `@ai-hero/sandcastle` **0.14.0** (npm latest, published 3 Nov 2026). It is not the `v1-next` prerelease and it does not use the v1 features from the explainer video.

The run used a **local** coding model only. Nothing paid was called.

## Reproduce

The default is Series C. It uses an already-running local OpenAI-compatible `/v1` endpoint. This kit does not bake in a host-specific address, and the script will not start, restart, or remove that server.

```bash
export OPENCODE_BASE_URL=http://<LLM_HOST>:8000/v1
./repro.sh
# same as:
# ./repro.sh --series c
```

Replace `<LLM_HOST>` with the address where that server already listens, as reached from a default-bridge sandbox. `OPENCODE_MODEL` defaults to `qwen/qwen3.8-27b-nvfp4`. If `OPENCODE_BASE_URL` is unset, the script exits with a clear error.

Series B starts a pinned `llama-server` (Qwen2.5-Coder-7B Q4_K_M) bound only to the default-bridge gateway, then runs the same task. Stop that server with `scripts/stop-llm.sh` when you are done.

```bash
./repro.sh --series b
```

Series A is the read-only OpenCode config mount (the agent never starts):

```bash
./repro.sh --series a
```

Useful flags: `--trials N` (default 3), `--skip-setup`, `--skip-probes`, `--help`. The script does not push anything. It does not print `OPENCODE_BASE_URL` or host addresses.

## What we ran

Sandcastle 0.14.0 has no first-party local-model or OpenAI-compatible base URL option. PR 676, which would have added `apiBaseUrl` to `opencode()`, was closed unmerged. The route that actually works is:

1. `opencode("llama/qwen2.5-coder-7b-instruct")`: Sandcastle's built-in OpenCode provider.
2. OpenCode's own `opencode.json`, pointing `@ai-sdk/openai-compatible` at a local `/v1` endpoint.
3. A local OpenAI-compatible endpoint. Series B used a pinned `llama-server` serving Qwen2.5-Coder-7B-Instruct Q4_K_M. Series C used an already-running local vLLM serving `qwen3.8-27b-nvfp4` (131k context, tool calling).

The official 0.14.0 init Dockerfile runs `npm install -g opencode-ai@latest`. This kit pins **1.19.5**, which was npm latest on 15 Nov 2026. That CLI still accepts the flags Sandcastle 0.14.0 issues (`run --format json`, `export` / `import`). Its help text lists `--auto` for permissions; `--dangerously-skip-permissions` is accepted and does not abort the process.

The coding task was a tiny ESM repo: implement `slugify` so `npm test` passes, then commit. The stub throws `not implemented`. Five tests fail on the baseline, confirmed before the runs.

## Results

See `logs/results-table.md` for the full table. Short version:

- Series A (three runs, ~11 s each) failed before the agent started: OpenCode 1.19.5 writes `.gitignore` into `~/.config/opencode` at startup, and that directory was bind-mounted read-only. That is a real pitfall when wiring a local model through OpenCode's config, not a Sandcastle crash.
- Series B (three runs, 62-81 s) used a writable config copy and a local Qwen2.5-Coder-7B Q4_K_M on llama-server. The agent started and then **failed the task**: 0 commits, tests still on the stub. The 7B model described the function, sometimes printed tool-call JSON as text, and emitted `<promise>COMPLETE</promise>`, which Sandcastle treated as done. That llama-server was torn down afterwards.
- Series C (three runs, 83-112 s) used the same harness and task, pointed at an already-running local Qwen3.8 27B vLLM with a tool-call parser. All three **passed**: one iteration, one commit (`Implement slugify`), `npm test` 5/5. The agent used real tools (`read`, `write` or `edit`, `bash`). The vLLM process was not started, restarted, or removed by this run.

The final Series B (3/3 fail) and Series C (live pass plus a `capDrop: ['ALL']` pass) share one harness commit: `b39e2c01face97b087c02d9e2d94c710e0bd35c8`. Same writable sandbox config except where the capDrop run is named.

Those outcomes are in `runs/` and `logs/`, with run IDs. They were not made up. A small local model that talks about edits is not the same as an agent that makes them, and the sandbox boundary is not the thing that decided Series B versus Series C.

Live tty captures (asciinema, then rendered to 1080p) are in `recording/`: `series-c-live.*` (107.8 s run, 110.6 s video), `series-b-live.*` (31.6 s run, 34.0 s video), and `probes-live.*` (host sibling-canary proof plus the sandbox miss). Redacted casts and transcripts sit beside each video. There is no recap video in this kit.

Screenshots in `screenshots/` are cropped frames from those live recordings, not illustrated recaps. Every terminal string in them is taken from the raw log.

## What the docker sandbox allowed and blocked

Probes used `createSandbox()` + `sandbox.exec()`, not the model, so the measurements do not depend on the agent behaving. Raw (redacted) output is in `runs/probes/`. Compared with the 0.14.0 docs:

| Documented default | Measured |
| --- | --- |
| Bind-mount worktree | Worktree mounted at `/home/agent/workspace` (read-write) |
| Numeric `--user`, default host uid:gid | numeric host uid:gid (the same ids as the user who started the run); `id` reported the sandbox user `agent` |
| No `--network` flag; Docker default bridge | `NetworkMode=bridge` |
| No `--cap-drop` unless set; Docker default caps | `CapDrop=null`. Bounding set still had the usual Docker defaults, including `NET_RAW` and `MKNOD`. The agent process itself had effective caps of zero |
| No `--privileged` | `Privileged=false` |

Enforcement:

- **Outside the workdir:** a canary next to the worktree (`sibling-canary.txt`) was created on the host and printed from the host (`ls`, `cat`, token `CANARY_TOKEN_NOT_A_SECRET`). The same relative path (`../sibling-canary.txt`) and the same absolute host path were invisible inside the sandbox (`No such file or directory`). An untracked canary in the checkout and a canary in the host `/tmp` were also invisible. The sandbox `/tmp` is private; a write there did not appear on the host. `../` from the worktree writes into the container's `/home/agent`, which is not a host escape.
- **Git control paths:** writes to `.git/config`, `.git/hooks`, and the worktree `.git` pointer were blocked (read-only overlay or "device or resource busy"), matching `protectGitMounts` in 0.14.0.
- **Network egress:** allowed on the default bridge. `https://example.com` and `https://www.cloudflare.com` both returned HTTP 200. Container localhost is not the host. The 7B llama-server was bound only to the default-bridge gateway, so the sandbox reached it there and not on container localhost. The already-running 27B vLLM was bound only to a host address the default-bridge sandbox could reach (`<LLM_HOST>`, port 8000); the default-bridge gateway and container localhost did not reach it. That is how the local models were wired, and it is also how an agent could reach the public internet (one planned command even included `git push`).
- **Root / capabilities:** not root, `sudo` not installed, `mknod` and `mount` failed. `ping` to loopback succeeded, likely via unprivileged ICMP sockets rather than `NET_RAW`. Default `docker()` had `CapDrop` unset and `CapEff=0` with the usual Docker bounding set. An extra Series C run with `capDrop: ['ALL']` still passed (74.6 s, 5/5 tests, one commit). Inspect of that container showed `CapDrop=["ALL"]` and `CapEff=CapPrm=CapBnd=0`. So the evidence supports zero effective capabilities on the default path, and also that this task still completes when all capabilities are dropped.

Two surprises worth keeping:

1. Bind-mounting the host `.git` at its absolute host path creates the parent path inside the container, including a `/home/<user>` prefix. It was owned by root and did not contain SSH keys, but the path itself is visible (`git rev-parse` prints it).
2. OpenCode will fail immediately if its config directory is read-only.

`CgroupParent=bench.slice` appeared on the container because this machine's Docker API was reached through an existing bench cgroup proxy, not because Sandcastle 0.14.0 has a cgroup option.

## Gaps

- 0.14.0 does not document a local or OpenAI-compatible model provider. The OpenCode config route is real, but it is OpenCode's, not Sandcastle's.
- This test used one small coding task. A 7B quantized model failed to use tools on that task (0/3). A local 27B model with a tool-call parser passed the same task (3/3). That does not measure a wider task set or other models.
- Permission behaviour for `--dangerously-skip-permissions` versus `--auto` was not separately proven beyond "the flag is accepted and the agent did not hang on a prompt."
- `capsh` was not on the default `PATH` inside the image (`/sbin`); capability claims use `/proc/self/status` and `docker inspect`.

## Layout

- `repro.sh`: one-command repro with pinned versions (default Series C)
- `versions.txt`: exact versions and checksums
- `harness/`: TypeScript runners, Dockerfile, OpenCode config, prompt
- `task-repo/`: the slugify kata
- `runs/`: raw per-run results and probe output (redacted)
- `logs/`: summaries and terminal typescripts (redacted)
- `screenshots/`: three stills, cropped from the live tty recordings
- `diagram/`: whiteboard of the three series (PNG plus source)
- `recording/`: live tty captures of one Series C run, one Series B run, and the enforcement probes, rendered to 1080p, with redacted casts and transcripts
