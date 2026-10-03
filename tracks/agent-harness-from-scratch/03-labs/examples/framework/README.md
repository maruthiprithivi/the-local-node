# Optional framework bridge

Core installation does not include a framework. Lesson 29's required path uses
an injected callback and the normal controller. This separate example uses
OpenAI Agents SDK **0.23.1**, reviewed at source commit
[`81f0ccf`](https://github.com/openai/openai-agents-python/tree/81f0ccf20c6e24063b9da36fa37f2bdb6a43d8d3).
The repository's pinned pyproject identifies this version and MIT license.
The maintained official [quickstart](https://openai.github.io/openai-agents-python/quickstart/)
and [running guide](https://openai.github.io/openai-agents-python/running_agents/)
document Agent, Runner, tools and bounded turns. This example has not been
installed or executed during source-only authoring.

Why this choice: a documented SDK makes the difference between model-boundary
convenience and orchestration ownership visible. `expose_operation` lets the SDK
request an existing harness operation, while `suggestion_adapter` lets the harness
request a single SDK suggestion. The SDK suggestion agent has no tools, handoffs,
session or fallback. Nested operations use `FrameworkToolBridge` and the exact
host registry/policy/controller/state. The bridge does not make arbitrary SDK
code safe: use trusted cooperative code or stronger isolation.

For an optional separate experiment, create a new environment and install this
directory's `requirements.txt` plus the editable core. Review dependency changes
and explicitly opt into live calls with a selected model. Credentials alone do
not enable either factory. This is a separate setup decision, not a required
exercise, test command or permission to spend money.

Both factories raise a clear error if disabled, absent or on an unreviewed SDK
version. Required offline tests do not import `agents`. Cancellation is checked
before/after calls; the optional request has an async timeout. Token/cost accounting
is unknown in the minimal SDK bridge, and a timeout may still incur remote usage.
