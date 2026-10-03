# Lesson 21: Tests organized by boundary

Prerequisite: Core track, especially lessons 6, 13 and 14; M6. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Tests have existed since lesson 1. Now separate pure value checks, provider contract checks, controller/policy/store integration and CLI/lifecycle checks. A unit test narrows diagnosis; integration catches interactions. Use temporary workspaces and injected clocks. The offline guard rejects unexpected network access.

## Diagram and text equivalent

```text
unit boundaries -> contract boundaries -> joined components -> CLI/lifecycle
```

Small checks isolate rules; joined checks verify that components preserve those rules together; interface checks verify usable behavior.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `tests/conftest.py; tests/contract/test_providers.py; tests/unit, tests/integration and tests/e2e; shared test fixtures`. Trace the relevant arguments and return values before editing.

Move a learner test into the narrowest appropriate test folder without changing its meaning. Add an integration test that closes and reopens a store while an exact approval or stop control is pending. Run single tests and then the suite on an approved execution host.

Create `tests/learner/test_lesson_21.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Return evidence from a new connection and close it; do not use global test state.

```python
def read_after_reopen(path, scope):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 21's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 21 --scenario coding
python -m course_harness checkpoint 21 --scenario sre
python -m course_harness checkpoint 21 --scenario automation
pytest -q tests -k lesson_21
pytest -q tests/learner/test_lesson_21.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
unit: changed action invalidates approval
contract: native response normalizes
integration: restart preserves pending state
E2E: CLI selects fake fixture and returns bounded stop reason
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Deliberately remove the human-stop read from the claim path in your learner branch. An in-memory test may still pass; a reopen-store integration test must fail. Restore the guard before continuing.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Write a regression test covering enqueue, pending approval, persistent stop, reopen and rejected admission/claim. Run it by itself and after an unrelated provider contract test; it must not depend on order.

1. Use tmp_path rather than a shared course-state.db.
2. Close the original connection before reopening.
3. Assert durable states and effect counts, not incidental model wording.

## Acceptance checks

Success and edge cases are independent; all scenario paths are offline; network guard rejects unexpected sockets; integration exposes the deliberate regression; live tests remain explicitly opt-in.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/21.md).

## Explain before continuing

Which test should fail if wire encoding changes but controller behavior does not? Which should fail if restart clears stop?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 21 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Add Windows-specific subprocess cleanup coverage on a permitted Windows runner; document gaps rather than simulating proof from Linux.
