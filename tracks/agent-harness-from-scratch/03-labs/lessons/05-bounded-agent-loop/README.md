# Lesson 5: The bounded agent loop

Lesson 4. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Connect model calls and tool results while keeping termination under controller control. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
model → validated tool request → tool result → model; controller budget guards every edge
```

Text equivalent: model passes into validated tool request passes into tool result passes into model; controller budget guards every edge. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/core.py) and locate `Engine.run`, `Limits`, and `RunResult`. Trace the successful path before editing.

Read one iteration of `Engine.run` aloud. Before a model call, check cancellation and remaining budgets. After a reply, distinguish final text from tool calls, validate unique identifiers, dispatch sequentially, and append matching results. A model that says 'keep going' cannot extend limits. Count failed and denied attempts according to the documented budget rules so retries cannot become free work.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Construct one controller from the provider, registry, and policy; there is no scenario-specific loop.

```python
from course_harness.core import Engine, Limits
from course_harness.providers import FakeProvider, Reply, ToolCall
from course_harness.tools import FixtureWorld, scenario_tools, Policy
world = FixtureWorld()
registry = scenario_tools(world)
provider = FakeProvider([Reply(calls=(ToolCall("r1", "observe_health", {}),)),
                         Reply("synthetic evidence only")])
result = Engine(provider, registry, Policy(allowed=frozenset({"observe_health"})),
                limits=Limits(steps=2)).run("inspect")
assert result.stop_reason == "final"
assert world.restarts == 0
```

Concrete exercise delta: Change only the scripted replies to add a second observation and then a looping case. In `Engine.run`, locate the checks before model calls and tool dispatch; write a test that would detect moving a check after execution.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 5 --scenario coding
python -m course_harness checkpoint 5 --scenario sre
python -m course_harness checkpoint 5 --scenario automation
pytest -q tests -k lesson_05
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Each result matches its request identifier; the successful script stops as final; the looping script stops as step_limit or call_limit. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Expect successful observation/final termination and `loop_stops: true` for a separately scripted looping run.

## Read a successful trace

```text
run_started -> model_called -> tool_requested -> tool_completed -> model_called -> run_stopped(final)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Return duplicate call identifiers or request more calls than the call limit. Check rejection/stop before the extra handler executes. An unmatched result must not be presented as evidence for another request.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Script two read-only calls then a final response for each scenario: read/list toy files; health/log evidence; event/plan inspection. Add a fake script that requests calls forever. Set a small step limit and verify a bounded stop.

Before opening the solution, write one learner test in a separate `test_learner_05.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Use a fresh scripted provider in every test.
2. Assert identifiers on recorded results, not just list length.
3. Place the limit check before work, then record the reason once.

[Reference solution and test reasoning](../../solutions/05.md). Try the first hint and your own test before reading it.

## Acceptance checks

Two-call success; identifier integrity; malformed/duplicate rejection; bounded looping; final reply makes no extra call. Add a test for a zero remaining call budget.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

Why can the provider not decide its own retry count? Does a tool error end every run? Which component chooses the stop reason?

Plain-language explanation: The loop is ordinary control flow: request, validate, execute only permitted work, feed back results, stop for a recorded reason.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Create a recoverable tool error followed by a final answer and inspect the changed trace.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
