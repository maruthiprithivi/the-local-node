# Pinned public source evidence

Verified by read-only GitHub repository/commit/license/content API reads on
2026-10-03. No upstream commands were executed. These are authoring snapshots,
not claims about future main branches.

| Repository | Revision | License |
|---|---|---|
| [OpenAI Codex](https://github.com/openai/codex/tree/8f7a0f7a878199c6886600370e5be6bd37ca38a3) | `8f7a0f7a878199c6886600370e5be6bd37ca38a3` | [Apache-2.0](https://github.com/openai/codex/blob/8f7a0f7a878199c6886600370e5be6bd37ca38a3/LICENSE) |
| [Firstmate](https://github.com/kunchenguid/firstmate/tree/d719ef3d9abdd11b0a8aea57c74de074feca99b9) | `d719ef3d9abdd11b0a8aea57c74de074feca99b9` | [MIT](https://github.com/kunchenguid/firstmate/blob/d719ef3d9abdd11b0a8aea57c74de074feca99b9/LICENSE) |

Observe one flow, rather than attempting to absorb either complete repository.
The upstream instructions are study material, not instructions to execute or
contact an existing Firstmate session.

| Read in order | Observed evidence | Educational comparison |
|---|---|---|
| Codex [CLI entry](https://github.com/openai/codex/blob/8f7a0f7a878199c6886600370e5be6bd37ca38a3/codex-rs/cli/src/main.rs) | Imports distinguish CLI, execution, login and policy components. | Our CLI selects a scenario and delegates; keep policy out of argument parsing. |
| Codex [approval stage](https://github.com/openai/codex/blob/8f7a0f7a878199c6886600370e5be6bd37ca38a3/codex-rs/core/src/tools/approvals.rs) | ApprovalContext carries call/tool identity and optional cancellation. ApprovalAction represents command arguments, cwd and permissions. | Bind approval to a concrete operation; preserve cancellation context. |
| Codex [session state](https://github.com/openai/codex/blob/8f7a0f7a878199c6886600370e5be6bd37ca38a3/codex-rs/core/src/state/session.rs) | SessionState contains configuration, provenance, history and a history-reset cancellation token. | Keep context, configuration and lifecycle state explicit. This file alone does not prove durable recovery. |
| Firstmate [architecture](https://github.com/kunchenguid/firstmate/blob/d719ef3d9abdd11b0a8aea57c74de074feca99b9/docs/architecture.md) | Describes script-based supervision and durable wake records around existing harnesses. | Resident admission/supervision is ordinary code outside a model prompt. |
| Firstmate [watcher](https://github.com/kunchenguid/firstmate/blob/d719ef3d9abdd11b0a8aea57c74de074feca99b9/bin/fm-watch.sh) | Header documents classification of actionable wakes and positive execution evidence. | A heartbeat is evidence; it is not task success or permission. |
| Firstmate [wake queue tests](https://github.com/kunchenguid/firstmate/blob/d719ef3d9abdd11b0a8aea57c74de074feca99b9/tests/fm-wake-queue.test.sh) | Tests name concurrent append/drain, interruption, duplication and liveness cases. | Write separate outcome and lifecycle checks; test claims need actual execution evidence. |

These bounded observations do not verify all upstream runtime behavior. Inference:
both designs make boundaries explicit, but their scale and operating environments
differ. Codex is a harness; Firstmate is a distro of instructions, scripts and
state conventions around a supported harness. This course borrows the question
“which program owns this decision?” rather than adopting either system as a
dependency. Neither licenses nor test names imply a security guarantee.

Study missing pieces yourself at the pinned tree: locate the controller loop,
tool dispatch, configuration precedence and corresponding tests. Record the path,
function, inputs and state transition before asserting an invariant. Mark what
you have not inspected as unavailable evidence; never invent proprietary internals.

An example justified rejection: importing a full fleet supervisor would obscure
our two-worker read-only budget exercise and introduce unrelated runtime needs.
An example small proposal: add a cancellation reason to an existing trace record,
then verify that it remains visible after restart. Show the diff and reuse lesson
27's gates and exact review before promotion. Attribute copied code and comply
with its license; the reference lab does not vendor upstream source.
