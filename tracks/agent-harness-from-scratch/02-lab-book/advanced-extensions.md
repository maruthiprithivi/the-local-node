# Extend the harness after understanding its boundaries

These four lessons extend the same package and scenario paths after the
framework-free core. They are small progressive lessons, not capstones. Core
installation and required tests remain offline and have no agent framework
dependency. Read [the issue addendum](https://github.com/maruthiprithivi/the-local-node/issues/5)
for the extension's scope; implementation/validation status remains in the track
README.

| Lesson | Extend | Read first |
|---|---|---|
| [29](../03-labs/lessons/29-framework-bridge/README.md) | Expose a gated tool and consume bounded framework suggestions | Lessons 4, 6, 16, 19 |
| [30](../03-labs/lessons/30-github-mentions/README.md) | Replay an authenticated GitHub mention through durable draft work | Lessons 7, 13, 14, 20 |
| [31](../03-labs/lessons/31-shared-memory/README.md) | Two users, consented sharing, conflicts and revocation | Lessons 6, 13, 15 |
| [32](../03-labs/lessons/32-harness-collaboration/README.md) | Separate harness instances with fenced durable ownership | Lessons 18, 24, 26, 31 |

## First create a tool you can explain

A tool starts as an ordinary Python function. Its contract says which fields are
required, which types are accepted and how large the result may be. Registration
gives it a stable name and discoverable description. The registry validates first;
policy then decides allow/deny/ask for the concrete operation. Only the authorized
executor invokes the function. The controller records its call ID, result/error,
usage and stop reason. A tool's description is not a permission grant.

Classify your fourth tool before registering it:

| Class | Example | Required boundary |
|---|---|---|
| Pure | Count synthetic events | Validated input/output limits; finite work |
| Read-only | Read a bounded toy file; inspect fixture service health | Explicit scope, freshness, size and cancellation |
| Side effect | Replace an approved local artifact; remediate the toy service | Exact approval/allowlist, preconditions, timeout, durable action identity, reconciliation |

Reuse lessons 4, 6 and 19's worked tools and contracts. Add a service-diagnostics
tool returning source/time/freshness and a gated remediation tool with a cooldown,
attempt bound and verified postcondition. They join the existing registry; the
agent loop should not gain a domain-specific branch. Test unknown fields, stale
approval, cancelled execution and structured failure before integrating a model.

Use the runnable [tool starter](../03-labs/examples/tool_creation.py),
[custom tool contracts](../03-labs/tests/contract/test_custom_tools.py) and
[worked solution](../03-labs/solutions/extensions.md). The starter proposes a
validated filtering extension for its bounded counter; the solution follows ordinary registration,
validation, host policy and execution rather than changing the loop.

## Framework integration has two directions

The optional example studies the OpenAI Agents SDK because its official docs
expose a small Agent/Runner API and document the runner's tool/handoff loop. An
Agent defines instructions; Runner obtains an output. The runner can also own
tools and handoffs, so this course deliberately keeps its instance suggestion-only
with no framework-managed tools or sessions. The educational controller retains
policy, state and lifecycle. See [official quickstart](https://openai.github.io/openai-agents-python/quickstart/)
and [Runner reference](https://openai.github.io/openai-agents-python/ref/run/).

The isolated example pins `openai-agents==0.23.1` and records source
`81f0ccf20c6e24063b9da36fa37f2bdb6a43d8d3`; consult its example README before a
separately authorized experiment. Required fixtures substitute an ordinary callback
for the SDK. Nothing imports or installs the framework during a core checkpoint.

Read the [isolated framework guide](../03-labs/examples/framework/README.md),
[pinned requirements](../03-labs/examples/framework/requirements.txt) and
[real SDK factories](../03-labs/examples/framework/bridge.py).
`expose_operation` decorates a wrapper that delegates to FrameworkToolBridge;
`suggestion_adapter` constructs the no-tool SDK Agent/Runner callback. Both remain
disabled until explicit enablement in a separately configured experiment. The
source-only authoring pass did not install or execute the optional SDK.

```text
framework callback -> suggestion provider -> existing controller -> gated tool
framework caller -> tool bridge -> existing controller/policy/journal -> result
```

Text equivalent: consuming framework output treats it like provider evidence.
Exposing a tool routes a framework call back through the same host controller,
policy and durable action journal. Neither direction creates a second authority
owner. The wrapper enforces calls, deadline and cancellation before/after a
cooperative callback; a hostile or hung callback needs process isolation.

## Mention-driven work: actual Claude action versus replay

The official Claude Code GitHub Action runs Claude Code inside repository
workflows. In its interactive mode, an `@claude` request triggers work after actor
checks; authenticated setup uses a GitHub App and a configured provider secret
or supported federation path. The action has configurable trigger phrases and
bot/non-write-user exceptions. Setup consumes runner and model resources and
requires a separate repository administration decision. These are source-study
facts, not setup instructions for this course. [Official guide](https://code.claude.com/docs/en/github-actions).

Authoring snapshot: [anthropics/claude-code-action at ed670b4cf9de2a5a570d130d2f6197b9e543cd64](https://github.com/anthropics/claude-code-action/tree/ed670b4cf9de2a5a570d130d2f6197b9e543cd64),
[MIT license](https://github.com/anthropics/claude-code-action/blob/ed670b4cf9de2a5a570d130d2f6197b9e543cd64/LICENSE),
[example workflow](https://github.com/anthropics/claude-code-action/blob/ed670b4cf9de2a5a570d130d2f6197b9e543cd64/examples/claude.yml)
and [action inputs](https://github.com/anthropics/claude-code-action/blob/ed670b4cf9de2a5a570d130d2f6197b9e543cd64/action.yml).
Read the [pinned security guide](https://github.com/anthropics/claude-code-action/blob/ed670b4cf9de2a5a570d130d2f6197b9e543cd64/docs/security.md)
before considering adaptation. It documents trigger access restrictions, bot
exceptions and risks from untrusted checked-out code with base-repository secrets.
The action's default PR behavior described there includes a branch and a creation
link, so do not assume every mention automatically creates a PR.

Our provider-neutral `@course-harness` replay is a different implementation:

```text
fixture delivery -> trusted authenticator -> repository/actor/base gate
 -> exact mention parser -> durable queue -> isolated toy change
 -> check receipt -> exact approval -> fake draft-PR receipt
```

Text equivalent: a verified fixture identity enters repository authorization and
the command parser. A bounded durable task produces a toy diff and check evidence.
Publishing requires exact approval, then creates a fake draft request. It never
merges. A synthetic raw-body HMAC signature demonstrates the fixture trust
mechanism; a JSON username is not real authentication, and this is not a webhook
server. The signing helper belongs only to the fake sender exercise.

For a later real receiver, authenticate Actions context through the trusted runner
or verify webhook signatures against raw bytes before parsing. Fetch current
repository access and exact base commit again before privileged work. Never put
comment text into a shell; never run untrusted PR code with privileged secrets;
never use `pull_request_target` to bypass trust boundaries. Keep live templates in
the examples directory, inactive outside `.github/workflows/`.

| Event or uncertainty | Required response |
|---|---|
| Redelivery / concurrent delivery | Stable logical key, bounded queue, one draft receipt |
| Edited/deleted comment | Re-fetch/cancel or invalidate earlier request; never assume text unchanged |
| Access revoked / fork / stale base | Reauthorize or reject before effects |
| Bot mention loop | Deny bots by default and bound actor/repository/global admission |
| Cancel / expired approval | Stop new work; invalidate changed/expired publication |
| Rate limit | Capped retry of reads or proven idempotent calls |
| Lost API acknowledgment | Inspect/reconcile by idempotency key before another create |

The tests prove the cases actually implemented in the fake client. Any omitted
live behavior must remain a documented gap, never be implied by a workflow sketch.
No apps, webhooks, grants, secrets, hosted jobs or paid calls are activated here.

## Shared memory is a service boundary

Start with two simulated authenticated users. Personal memory remains private;
an owner explicitly selects a record to publish into an authorized project/team
scope. Store owner, provenance, scope, version, timestamp, retention and access
policy. Check read/search/write/delete authorization before content reaches a
provider. Prompt instructions and post-retrieval filtering cannot fix a leak.

Use optimistic versions: an edit supplies the version it observed; a mismatch
surfaces conflict instead of overwriting another user's correction. Deletion
and revision/cache invalidation prevent deleted values resurfacing. This fixture
erases rows/history and bumps a scope revision; it does not retain content-bearing
tombstones. Revocation
blocks future access; it cannot erase what was already disclosed. The SQLite
fixture is a local service demonstration, not a file to share across machines or
a production identity/authorization system.

## Separate harnesses need ownership, not just memory

Workers inside one harness share a controller. Separate harness instances have
their own provider, executor and policy. A versioned envelope carries correlation,
principal, scope, capabilities, artifact references, deadline, remaining budget and
idempotency key. A coordinator supplies durable leases and increasing fencing
tokens. A receiver reauthorizes locally; sender authority never becomes receiver
authority. Shared memory can supply evidence but cannot lock a task.

An expired owner may still be running during a partition. The fencing token
rejects that owner's stale result. Duplicate/out-of-order deliveries must not
create a second logical effect. Propagate cancellation and total budgets through
delegation; cap fan-out. Reconcile a lost receipt before retry and surface
conflicts. The default demonstrates these mechanics through deterministic local
transport fixtures. Real multiple processes, multi-host transport, authentication,
isolation and failover require additional validation and hardening.

Run the extension integration modules only on a permitted execution host:

```sh
pytest -q tests/integration/test_extensions.py
pytest -q tests/integration/test_team.py
```

Those are commands to execute, not a passing report. Each lesson gives its own
checkpoint, concrete TODO, hints, failure, solution and explanation question.
