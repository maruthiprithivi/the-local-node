# Lesson 23: Stress, injection and failure testing

Prerequisite: Lessons 14, 21 and 22; M6. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

A failure matrix names injection point, expected state, permitted effects and recovery. Cover malformed replies, rate limits, huge output, queue storms, storage failure, stale approval, expired lease, hung callback, injected instructions, traversal/symlink attempts and crashes after effects. Use synthetic fixtures; do not probe real infrastructure.

## Diagram and text equivalent

```text
injected fault -> boundary decision -> bounded state -> inspect/reconcile
```

A synthetic fault reaches a named boundary; a deterministic check proves a limit or explicit uncertain state, then recovery uses evidence.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `core.py budgets/retry/context; tools.py validation/path gates; resident.py enqueue/recover; persistence.py uncertain states; advanced.py StreamAssembler`. Trace the relevant arguments and return values before editing.

Choose one boundary, add a failing fixture and a precise expected state. Fix the smallest bug without broadening policy. For a queue storm, assert accepted task count never exceeds capacity and rejected events remain visible to the caller.

Create `tests/learner/test_lesson_23.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Handle explicit capacity failure without retrying indefinitely; other state failures should remain visible.

```python
def admit_burst(queue, events):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 23's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 23 --scenario coding
python -m course_harness checkpoint 23 --scenario sre
python -m course_harness checkpoint 23 --scenario automation
pytest -q tests -k lesson_23
pytest -q tests/learner/test_lesson_23.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
burst exceeds queue capacity -> explicit QueueFull
expired running lease -> uncertain, not queued
untrusted log says disable policy -> policy remains unchanged
human stop persists across reopen
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Use a callback that mutates a toy artifact and raises before recording completion. Treat its result as uncertain; inspect the artifact before resolution. A thread-based cooperative runner cannot forcibly kill a malicious/hung callback; list that unsupported threat.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Add one adversarial case that first reveals a real regression in your learner branch, then fix it. Include a test for cancelled partial streams returning no calls and a paragraph identifying what the test does not prove.

1. Count effects with a temporary fixture file or list.
2. Inject clocks instead of waiting for real leases.
3. A BoundaryError is useful only if the executor has not already performed the denied action.

## Acceptance checks

Limits hold during storms; stale approvals reject changed operations; prompt injection cannot change host policy; expired effects are uncertain; stop survives; dead-letter states are inspectable; residual risks are documented.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/23.md).

## Explain before continuing

What is the difference between testing a path restriction and proving isolation? Why is unavailable storage a reason to stop before an unrecorded effect?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 23 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Create a matrix table for every critical transition and add process-isolated hung-tool experiments only in a separately authorized disposable environment.
