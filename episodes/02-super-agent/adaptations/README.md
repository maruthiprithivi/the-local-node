# Adaptations A1–A6

The prototype is written for github.com and a normal desktop. Running it in a locked-down sandbox against a local
Gitea forge needed six small changes. They are reproduced here as
generic code. None of them changes how the orchestrator routes work or how the worker solves a task.

| id | where it applies | file | what it does |
|---|---|---|---|
| A1 | image build (mode a) | `A1-forge-credential-helper.sed` / `.patch` | Adds one `[credential "http://127.0.0.1:3000"]` line next to the prototype's `[credential "https://github.com"]` line in `src/infra/environment.ts`. Without it, the worker's git cannot authenticate to the forge. |
| A2 | image (both modes) | `A2-gh-shim/gh` | A `gh`-compatible shim. It maps the prototype's `gh` / `gh api` calls to the forge's REST API and rewrites forge URLs to github.com form, because the prototype's URL parser accepts only github.com. Configured as the prototype's Agent GitHub CLI (via `~/.local/bin/gh-agent`) in mode a and as `gh` in mode b. It reads `FORGE_URL`, `FORGE_TOKEN` / `FORGE_TOKEN_FILE` and `FORGE_LOGIN`. Nothing is hardcoded. |
| A3 | mode a start | `A3-start-without-tmux.sh` | tmux cannot get a pty in the sandbox. This script starts the same `dsh --profile superagent --no-open` command with setsid/nohup, and `scripts/dsh-superagent start` adopts the running process. |
| A4 | mode a setup | `A4-status-mainthread.sh` | The status script's process finder also accepts the thread name `MainThread`, because that is what Node 24 calls dsh's main thread. |
| A5 | mode a settings | `A5-mode_a_config.py` (`PREPARE`) | The executor prepare command fetches from the forge URL instead of `https://github.com`. Otherwise it is the prototype's documented example. |
| A6 | image build (mode a) | `A6-dsh-scope-peer.sh` | The linked plugin bundle loaded its own dev-installed copy of `@deepseek-ai/dsh-scope` (0.2.1-alpha.2 in our build). That broke the worker's tool allow-list: the worker got only the orchestrator tools and `subagent`, with no bash/read/write. A6 symlinks that one peer to the installed dsh's copy. |

**Rerun disclosure.** Mode-a t1-r1 was rerun under A6. The pre-A6 attempt failed: no PR; the worker had
no bash/read/write tools, probed for them, then handed the ticket back to a person. It is not counted in the matrix.
b-t1-r1 ran on the pre-A6 image. A6 only affects the prototype bundle, which mode b does not load. dsh
0.2.1-rc.2 was used for all matrix runs. (The prototype's own docs pin 0.2.1-rc.3, and that version is also on npm.
To match our numbers, use rc.2.)

**Security note on A2.** `gh auth token` prints the token, like the real `gh`. We kept that on purpose because the
reach check tests for it. Set `GHCOMPAT_DENY_AUTH_TOKEN=1` to refuse it.
