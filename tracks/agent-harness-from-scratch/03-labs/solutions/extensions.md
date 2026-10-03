# Extension solutions and worked custom tool

Try the numbered exercises and hints before reading these worked paths:

- [29: framework bridge in both directions](29.md)
- [30: authenticated mention replay](30.md)
- [31: selected memory publication](31.md)
- [32: bounded peer ownership](32.md)

The required path uses standard Python fixtures. Neither this guide nor a passing
offline test activates the optional SDK, GitHub workflow or hosted shared service.

## Complete a small diagnostics tool

This fourth tool is a plain read-only Python function, with input/result contracts,
a stable discoverable name, explicit target and host policy. Put it and its tests
in your learner test file. It reads only FixtureWorld; no host service is probed.

```python
from course_harness.core import Engine
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.tools import (
    Tool, Registry, Policy, FixtureWorld, object_schema, validate,
)

SERVICE = {"type": "string", "enum": ["toy-service"], "maxLength": 32}
RESULT = object_schema(service=SERVICE, healthy={"type": "boolean"},
                       source={"type": "string", "maxLength": 64})

def diagnostics_tool(world):
    def inspect(arguments):
        result = {"service": arguments["service"], "healthy": world.healthy,
                  "source": "synthetic_service"}
        validate(result, RESULT, "result")
        return result
    return Tool("diagnostics", "Inspect only toy-service synthetic health",
                object_schema(service=SERVICE), inspect,
                effect="read", target="toy-service")

def diagnostics_run(world, arguments, *, permitted=True):
    registry = Registry([diagnostics_tool(world)])
    policy = Policy(allowed=frozenset({"diagnostics"}) if permitted else frozenset())
    provider = FakeProvider([
        Reply(calls=(ToolCall("diagnosis-1", "diagnostics", arguments),)),
        Reply("Synthetic observation received; diagnosis remains a hypothesis."),
    ])
    return Engine(provider, registry, policy).run("Inspect the toy fixture only.")

def test_custom_diagnostics_success():
    world = FixtureWorld()
    result = diagnostics_run(world, {"service": "toy-service"})
    assert result.stop_reason == "final"
    assert world.restarts == 0

def test_custom_diagnostics_denied():
    world = FixtureWorld()
    result = diagnostics_run(world, {"service": "toy-service"}, permitted=False)
    assert result.stop_reason == "denied"
    assert world.restarts == 0
```

Add invalid-field, wrong-service, malformed-result and cancelled-run tests. Count
handler invocations to prove invalid arguments never reach it. Registry.prepare
validates the input before policy/execution; the handler validates its own output.
The Engine records structured errors and bounded output. A finite pure fixture
callback is cooperative; a blocking external diagnostics command would need the
restricted executor, timeout and process cleanup from lesson 10. Cancellation
cannot forcibly interrupt arbitrary Python in this example.

For remediation, expose the existing toy restart handler only through Policy and
the durable Engine seam. Use an exact service allowlist, cooldown/attempt bound,
preconditions, stable action ID and observed postcondition. A stale approval or
uncertain started action must not be treated as permission to repeat the restart.
Do not call execute directly to bypass the gate.

## Both framework directions

Required offline callback:

```python
from course_harness.extensions import FrameworkProvider
from course_harness.providers import Reply

provider = FrameworkProvider(
    lambda messages, tools: Reply("Read-only fixture suggestion"), max_calls=1)
reply = provider.complete([{"role": "user", "content": "inspect fixture"}])
assert reply.text == "Read-only fixture suggestion"
```

Required exposure of a host tool uses FrameworkToolBridge from lesson 29. The
optional SDK counterpart is in `examples/framework/bridge.py`: `expose_operation`
decorates a wrapper that delegates to that bridge; `suggestion_adapter` uses an
Agent with empty tools/handoffs and a one-turn Runner request. It requires explicit
enablement, an exact reviewed SDK version, model selection and bounded timeout.
Read that source as the worked SDK example; do not install or run it as part of
ordinary acceptance. The optional factory is source-reviewed and unexecuted;
provider usage remains unknown in this minimal adapter.

## Mention and team mechanisms

The GitHub exercise verifies a synthetic HMAC over raw fixture bytes. Fresh fake
API records supply actors and repository permission; event JSON cannot impersonate
a caller. `sign` is a fake sender helper, not a real receiver endpoint. A toy
Engine diff and synthetic state check make a reviewable artifact. The publication
method assumes a trusted operator supplies the reviewed digest; a real deployment
needs authenticated review and durable consent. It never merges.

The team exercise mints contexts through a fake trusted authenticator. Access is
checked before retrieval; selected publication is consented; version conflicts,
deletion, retention and membership changes invalidate future reads. Coordination
uses versioned envelopes and fenced leases. Identical receipt replay can reconcile
a lost acknowledgment, while unrecorded writes need current ownership. These are
single-host service mechanics, not multi-host consensus or real identity proof.

Run only on your permitted execution host:

```sh
pytest -q tests/integration/test_extensions.py
pytest -q tests/integration/test_team.py
```

Expected test outcomes are described in the numbered solutions. Report actual
executed checks, environment and failures separately from these authored examples.
