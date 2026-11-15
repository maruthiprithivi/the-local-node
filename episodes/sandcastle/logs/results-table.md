# Results (Asia/Singapore)

Task: implement `slugify` in a tiny Node repo so `npm test` passes, then commit.
Baseline before every run: 5 failing tests (`not implemented`).

Harness commit used for the final Series B and Series C runs below (identical sandbox config: writable OpenCode config, same image, no extra `capDrop` unless named): `b39e2c01face97b087c02d9e2d94c710e0bd35c8`.

## Series A - read-only OpenCode config mount

The first wiring put `opencode.json` on a **read-only** bind mount at `~/.config/opencode`. OpenCode 1.19.5 tries to write `.gitignore` there at startup, so the agent never ran.

| run id | pass/fail | wall | iterations | commits | what happened |
| --- | --- | --- | --- | --- | --- |
| trial-1-20261115T021452 | FAIL | 11.4 s | 0 | - | `opencode` exit 1: `FileSystem.writeFile (~/.config/opencode/.gitignore)` |
| trial-2-20261115T021504 | FAIL | 11.3 s | 0 | - | same error |
| trial-3-20261115T021516 | FAIL | 11.2 s | 0 | - | same error |

## Series B - writable config, local Qwen2.5-Coder-7B Q4_K_M (llama-server)

Three runs on the final harness (`b39e2c0`). The agent started and then failed the task: 0 commits, tests still on the stub. The 7B model printed tool-like shell or JSON as text, then emitted `<promise>COMPLETE</promise>`. trial-b-1-20261115T024800 is the live tty recording.

| run id | pass/fail | wall | iterations | commits | test after | what happened |
| --- | --- | --- | --- | --- | --- | --- |
| trial-b-1-20261115T024800 | FAIL | 31.6 s | 2 | 0 | 1 (still stub) | Printed `read`/`write`/`npm test`/`git commit` as a bash script, including `module.exports`, then `echo "<promise>COMPLETE</promise>"` (live recording) |
| trial-b-1-20261115T024854 | FAIL | 23.7 s | 1 | 0 | 1 (still stub) | Same pattern: described the edit in text, no commit |
| trial-b-1-20261115T025346 | FAIL | 46.4 s | 3 | 0 | 1 (still stub) | Printed `edit`/`bash command=` as text, then `<promise>COMPLETE</promise>` |

The Series B llama-server was torn down after these three runs. It was not the already-running 27B server.

## Series C - same harness, already-running local Qwen3.8 27B (vLLM, tool calling)

Same Sandcastle 0.14.0 + OpenCode 1.19.5 + the same slugify task + the same writable sandbox config as Series B. The model is `qwen3.8-27b-nvfp4` on an already-running local vLLM (131k context, `qwen3_xml` tool parser, no API key). From the default-bridge sandbox the server was reachable on a host address at port 8000 (`<LLM_HOST>`), and not on the default-bridge gateway or container localhost. That server was not started, restarted, or removed by this kit. trial-c-1-20261115T025447 is the live tty recording.

| run id | pass/fail | wall | iterations | commits | test after | what happened |
| --- | --- | --- | --- | --- | --- | --- |
| trial-c-1-20261115T025447 | PASS | 107.8 s | 1 | 1 (`9ed0712` Implement slugify) | 0 (5/5 pass) | Real tools: read, write, `npm test`, commit (live recording) |
| trial-c-1-20261115T025654 | PASS | 74.6 s | 1 | 1 (`caf9d30` Implement slugify) | 0 (5/5 pass) | Same task with `docker({ capDrop: ['ALL'] })`. Inspect: `CapDrop=["ALL"]`, `CapEff=0`, `CapBnd=0`. Still passed. |

An earlier three-run Series C pass (83-112 s, 1 commit each, 5/5) was recorded on the same machine and task before this harness commit; those run ids remain under `runs/trial-qwen38-*`.

## capDrop

Default `docker()` runs had `CapDrop=null` and `CapEff=0` with the usual Docker bounding set. The extra Series C run with `capDrop: ['ALL']` still passed, and inspect showed `CapDrop=["ALL"]` and `CapEff=CapPrm=CapBnd=0`. The evidence supports both: default runs have zero effective capabilities, and the agent can still complete this task when all capabilities are dropped.
