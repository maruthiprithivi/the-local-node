# Lesson 29: Integrate a framework after learning the internals

Prerequisites: Core course and lessons 16/19. This extends the same engine after the core course;
there is no new final project. Work from `03-labs/` after setup. Complete this
lesson in three small sessions: trace the boundary, implement/test the delta,
then explain the outcome. Required work remains offline.

## What we build and why

A framework may supply suggestions or call a host operation. It must not become a second policy, session or side-effect owner. The optional OpenAI Agents SDK example is isolated from core dependencies; its no-tool/no-session callback returns a suggestion. FrameworkToolBridge routes a requested tool through the existing Engine, registry, Policy and optional journal.

## Diagram and text equivalent

```text
framework suggestion -> provider boundary -> host engine; framework tool call -> bridge -> host engine/policy/store
```

Both directions cross the same host boundary. The framework produces evidence; the controller and policy retain termination and authority.

## Read and implement one delta

Open [extensions.py](../../src/course_harness/extensions.py) and inspect
`FrameworkProvider.complete and FrameworkToolBridge.invoke; examples/framework/`. Keep the controller, policy and store ownership visible.
Read [the extension guide](../../../02-lab-book/advanced-extensions.md).

The optional [framework example guide](../../examples/framework/README.md),
[SDK factory source](../../examples/framework/bridge.py) and
[pinned requirements](../../examples/framework/requirements.txt) show the actual
`expose_operation` and `suggestion_adapter` implementations using SDK 0.23.1.
The required callback comparison below runs without SDK installation or import.
Review the [custom tool starter](../../examples/tool_creation.py) and
[contract checks](../../tests/contract/test_custom_tools.py) before exposure.

Create `tests/learner/test_lesson_29.py` and start with this helper:

```python
def read_through_bridge(registry, policy):
    # TODO: Use FrameworkToolBridge with a finite call budget; request only observe_health.
    raise NotImplementedError("Complete the learner boundary")
```

Write a successful assertion and an edge case before filling the TODO. Use
synthetic inputs and inspect effect counts; do not replace host authorization
with model confidence. [Separate solution](../../solutions/29.md).

## Commands and expected evidence

```sh
python -m course_harness checkpoint 29 --scenario coding
python -m course_harness checkpoint 29 --scenario sre
python -m course_harness checkpoint 29 --scenario automation
pytest -q tests/integration/test_extensions.py
pytest -q tests/learner/test_lesson_29.py
```

Expected: checkpoint JSON identifies the lesson/scenario and contains true
boundary checks plus a finite stop reason. Tests should select and execute useful
checks, not report zero selection. The final command exists after you author the
learner test. These are execution instructions, not a claim of a passing run on
the source-only Mac. Check current remote validation evidence in the track README.

## Readable successful trace

```text
framework invokes observe_health -> validation -> policy allow -> result -> final
framework invokes restart_service -> policy denied; restarts=0
suggestion callback -> bounded Reply; extra call -> framework_budget
```

The trace describes semantic order. Look for corresponding IDs, decisions and
receipts in actual output; fixture/helper events need not use these literal names.
Coding uses disposable files, SRE uses synthetic observations and automation uses
local fixture events throughout this extension.

## Controlled failure

Let the framework request restart_service under a host policy permitting only observe_health. The bridge must stop denied with no restart. Then cancel before a callback and exhaust its call bound. The wrapper checks cooperative elapsed time after return; it cannot forcibly stop hung code.

Predict the permitted effect count and durable state before replaying the fault.
Keep failed input separate from the reference fixture and restore it afterward.

## Exercise and progressive hints

Compare the same read-only synthetic health task through FakeProvider and through the bridge. Add one permitted custom diagnostics tool and one gated remediation request. Explain which lines become simpler and which boundary checks remain. Test cancellation and denied nested calls.

1. Build scenario_tools(FixtureWorld()) once; do not introduce a parallel registry.
2. Bridge.invoke returns RunResult with stop_reason and trace.
3. Keep framework-managed tools empty in the optional SDK suggestion callback; route explicit host operations through the bridge.

## Automated acceptance checks

Core imports/runs without the framework; missing optional dependency fails clearly; nested denied actions never execute; call limits, cancellation and timeout evidence remain visible; one host journal owns effects; no implicit fallback.

Reference integration checks cover the delivered mechanism; your test verifies
your own incremental delta. Remove the guard once to prove your test detects the
regression, then restore it. Mark missing live integration, actual authentication,
process isolation or multi-host behavior explicitly rather than inferring it from
an offline fixture pass.

## Self-check and plain explanation

What can the framework replace, and which responsibilities must remain host-owned? Why isn't an SDK tool decorator sufficient permission enforcement?

Explain the input, the trusted host decision, the untrusted evidence and the
resulting stop/recovery state. A simulated identity, check receipt or reviewer is
useful for a deterministic exercise; it is not proof of a production boundary.

## Checkpoint and optional continuation

Re-run checkpoint 29 to inspect the reference mechanism without overwriting
your learner branch. Preserve your diff before experimenting.

After separate authorization and remote validation, compare the pinned SDK callback with the offline callback using the same evaluation fixtures; installation/live inference is not part of this checkpoint.
