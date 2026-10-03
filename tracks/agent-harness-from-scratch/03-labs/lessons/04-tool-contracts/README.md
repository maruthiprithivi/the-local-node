# Lesson 4: Tool contracts and explicit dispatch

Lesson 3. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Validate a structured request before any handler executes. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
ToolCall → named contract validation → registry lookup → handler → structured result
```

Text equivalent: ToolCall passes into named contract validation passes into registry lookup passes into handler passes into structured result. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/tools.py) and locate `Tool`, `Registry`, and tool argument validators. Trace the successful path before editing.

Add a pure tool before a file operation. The registry maps names to explicit handlers; it never evaluates generated Python. Validate required fields, extra fields, types, and size bounds. Python booleans are a subtle case: `bool` is a subclass of `int`, so decide deliberately whether a boolean satisfies a numeric field. Return structured errors that identify the boundary without dumping huge inputs. Keep tool result shape independent of conversational prose.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Provider SDKs and our tools are different boundaries

An SDK is a software development kit: a library supplied to help call an external API. An official provider SDK could replace the thin HTTP transport in [lesson 3](../03-shared-llm-helpers/README.md), while our shared helper still normalizes its response into `Reply` and `ToolCall`. The delivered helpers use standard-library HTTP, so this walkthrough installs no SDK.

A registry tool is our own Python function with a name and argument contract. A provider's tool-calling feature returns a request naming it; it does not run the function. `Registry.prepare` checks that request, host `Policy` decides permission, and the executor calls the handler. You can write tools without any provider SDK or agent framework.

## Build a basic tool, one step at a time

Create `examples/count_fixture_rows.py` on your learning branch. This new file is your exercise work, separate from the delivered checkpoint. The tool will count at most eight rows from one fixed synthetic fixture. It reads no files and performs no network or system action.

### 1. See the missing registration fail

```python
from course_harness.tools import Registry

registry = Registry([])
try:
    registry.prepare("count_fixture_rows", {"fixture": "coding", "limit": 8})
except ValueError as error:
    print(error)
```

Expected printed error: `unknown tool`. This is useful failure: there is no implicit function discovery or evaluation of generated code. Registration is an explicit source change.

### 2. Write the handler and exact contract

Put this beneath your imports. A handler takes one validated argument dictionary and returns a small result dictionary.

```python
from course_harness.tools import Tool, object_schema

FIXTURE_ROWS = {
    "coding": ("calculator.py", "test_calculator.py"),
    "sre": ("health observation", "metric sample", "fixture log"),
    "automation": ("daily-summary event",),
}

def count_fixture_rows(arguments):
    rows = FIXTURE_ROWS[arguments["fixture"]]
    return {"fixture": arguments["fixture"],
            "count": len(rows[:arguments["limit"]])}

count_tool = Tool(
    name="count_fixture_rows",
    description="Count a bounded selection from a synthetic fixture",
    parameters=object_schema(
        fixture={"type": "string",
                 "enum": ["coding", "sre", "automation"], "maxLength": 16},
        limit={"type": "integer", "minimum": 0, "maximum": 8},
    ),
    execute=count_fixture_rows,
    effect="read",
    target="synthetic_fixture_rows",
)
```

`object_schema` makes both fields required and forbids extra fields. The supported validator also checks the fixture enum and rejects numeric strings, booleans, negative limits, and limits above eight. A zero limit intentionally returns zero. Here `limit` bounds selection; fixed fixture rows bound the available data. We are not pretending the validator implements `maxItems` for arbitrary arrays.

### 3. Register, validate, then call

```python
registry = Registry([count_tool])
arguments = {"fixture": "coding", "limit": 8}
selected = registry.prepare("count_fixture_rows", arguments)
print(selected.execute(arguments))
```

Expected result: `{'fixture': 'coding', 'count': 2}`. Unlike the first step, the name now resolves. Do not call the handler directly with unvalidated model input. This isolated pure-function demonstration omits policy; the engine path below includes it.

### 4. Dispatch through the same tiny engine

```python
from course_harness.core import Engine, Limits
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.tools import Policy

provider = FakeProvider([
    Reply(calls=(ToolCall("count-1", "count_fixture_rows", arguments),)),
    Reply("Counted the coding fixture; no side effect occurred."),
])
policy = Policy("read_only", frozenset({"count_fixture_rows"}))
result = Engine(provider, registry, policy, limits=Limits(steps=2)).run(
    "Count the coding fixture rows."
)
print(result.stop_reason)
print([event["event"] for event in result.trace])
```

Expected stop reason: `final`. Expected event order:

```text
run_started → model_called → tool_requested → tool_completed → model_called → run_stopped
```

Text equivalent: start the run; obtain a structured request from the fake; validate and authorize it; execute the registered handler; feed its result into the next model call; stop on the final reply. Inside this flow, `tool_requested` records decision `allow`. The result message is linked to `count-1`. Lesson 5 examines this loop in detail; here it proves your new tool fits the shared boundary.

The complete solution and pytest checks live separately. Copy the worked code into your own file, then change its exercise behavior below. Required runs remain offline.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 4 --scenario coding
python -m course_harness checkpoint 4 --scenario sre
python -m course_harness checkpoint 4 --scenario automation
pytest -q tests -k lesson_04
python examples/count_fixture_rows.py
pytest -q test_learner_04.py
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. The final two commands refer to files you create from this walkthrough/solution; they do not exist until you create your exercise. With the four worked steps combined in order, your example prints `unknown tool`, the coding count dictionary, `final`, and the six-event list. Expected checkpoint CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

A valid request invokes exactly its named handler once; invalid requests produce contract errors and zero effects. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Expect one harmless observation, final termination, and `unknown_rejected: true` in the baseline checks.

## Read a successful trace

```text
tool_requested -> arguments_validated -> handler_selected -> tool_completed
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Request `count_fixture_rows` before registration, omit `limit`, then pass `"8"` or `True` instead of an integer. Also try `{"fixture": "production", "limit": 8}` and an extra `command` field. Each must fail in `Registry.prepare` before the handler runs. Use a spy/counter to prove zero execution, not merely to match an error message.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Implement the new `count_fixture_rows` tool in your exercise file, starting with an empty registry so the first test fails as `unknown tool`. Add registration to make that test pass. Then add a required `nonempty_only` boolean to its contract and filter empty fixture rows before applying the limit. Seed one empty row in each scenario fixture and prove it is counted only when `nonempty_only` is false. Change the handler and contract together; do not silently accept an extra field. The new behavior should make a learner-written test fail against the original two-field tool.

Before opening the solution, write one learner test in a separate `test_learner_04.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Keep the enum and integer limit rules; add a boolean rule for the new required field.
2. Filter before slicing so the limit counts selected nonempty rows rather than consuming slots with empty entries.
3. A handler counter proves invalid requests never execute; a fake tool-call/result identifier proves successful dispatch is linked correctly.

[Reference solution and test reasoning](../../solutions/04.md). Try the first hint and your own test before reading it.

## Acceptance checks

Check registration failure then success; counts for all three fixtures and limit zero; required-field/extra-field/enum/type/numeric-bound failures; boolean-as-integer rejection; zero handler calls on invalid arguments; one linked engine result with final termination. Add your filtering test as the learner-written extension. The solution contains complete pytest examples for these checks.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Why is a natural-language description insufficient? What is the difference between validation and policy? What does a provider SDK call, and what calls your registered tool handler? Why not use `eval` for a clever tool?

Plain-language explanation: Contracts make operations predictable. They establish shape and bounds; policy will separately establish whether an otherwise valid operation is permitted.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Add a structured error code and assert it without depending on full prose.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
