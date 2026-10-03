# Lesson 12: Retries, deadlines, cancellation, and budgets

Lesson 11. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Recover from transient failures with bounded work and honest uncertainty. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
attempt → classify error → terminal stop OR capped delay → recheck stop/deadline → attempt
```

Text equivalent: attempt passes into classify error passes into terminal stop OR capped delay passes into recheck stop/deadline passes into attempt. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/core.py) and locate `retry_call`, `Limits`, cancellation, and deadline checks. Trace the successful path before editing.

Classify terminal authentication/contract failures separately from retryable rate limits or transient transport errors. Cap attempts and delay; inject clock, sleeper, and deterministic jitter so tests need no real waiting. Bound each request and the entire run. Check cancellation before new work and during waiting. Share budgets across retry attempts. A timeout after a side effect means 'possibly completed,' not 'safe to repeat.' Retry model transport differently from uncertain mutations.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Use injected time for retry mechanics; a test need not actually wait.

```python
from course_harness.core import retry_call
state = {"now": 0.0, "calls": 0}
def operation():
    state["calls"] += 1
    if state["calls"] == 1:
        raise TimeoutError("fixture")
    return "recovered"
def sleeper(delay):
    state["now"] += delay
assert retry_call(operation, retryable=lambda e: isinstance(e, TimeoutError),
                  sleep=sleeper, clock=lambda: state["now"], attempts=2) == "recovered"
assert state["calls"] == 2
```

Concrete exercise delta: Add cancellation during sliced sleep and deadline-before-next-attempt cases to `retry_call`. Keep uncertain mutations out of this helper. If you integrate provider retries into `Engine.run`, count every attempt against the existing run budget rather than allocating a new one.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 12 --scenario coding
python -m course_harness checkpoint 12 --scenario sre
python -m course_harness checkpoint 12 --scenario automation
pytest -q tests -k lesson_12
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Transient recovery uses bounded attempts; terminal errors stop; cancellation prevents new work; uncertain non-idempotent effects require reconciliation. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Expect final termination and `bounded_retry: true` from a separate fake-clock helper check. Retry helper behavior and controller integration are distinct surfaces to inspect.

## Read a successful trace

```text
model_called -> retryable_error -> bounded_backoff -> model_called -> final; cancelled -> run_stopped(cancelled)
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

A cancelled backoff should not trigger its next call. A terminal error should produce only one attempt. A continuously retryable error must reach the ceiling/deadline.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Script a transient failure then success, repeated rate limiting, terminal authentication failure, and cancellation during backoff. Add a synthetic effect that mutates before timing out; confirm it enters uncertainty rather than automatically executing twice.

Before opening the solution, write one learner test in a separate `test_learner_12.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. A fake sleeper advances fake time; it need not sleep.
2. Place stop checks on both sides of a delay.
3. Do not give retries a fresh run budget.

[Reference solution and test reasoning](../../solutions/12.md). Try the first hint and your own test before reading it.

## Acceptance checks

Capped retry success/failure; terminal no-retry; fake-clock deadline; cancellation propagation; uncertain effect not repeated. Add a deadline that expires during backoff.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

How does deadline differ from timeout? Why can a server finish after the client timed out? Which retries are safe without observing state?

Plain-language explanation: Reliability means bounded recovery and truthful state, not trying forever or assuming a timeout erased an effect.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Honor a bounded retry-after hint using the same deadline and fake clock.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
