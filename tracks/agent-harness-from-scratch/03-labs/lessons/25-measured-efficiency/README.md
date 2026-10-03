# Lesson 25: Efficiency without weakening gates

Prerequisite: Lessons 22 and 24; M7. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Measure first: redundant read count, context characters, steps, queue wait, usage and outcome. Cache only read observations with scope, logical key, state version and configuration version. JSON copies prevent caller mutation of the cached snapshot. A cache must never execute or verify a side effect.

## Diagram and text equivalent

```text
scoped versioned read key -> hit / bounded loader -> copied observation
```

A matching scope/state/config key returns a copied observation; changed versions force a new read.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: ReadCache.read and compare_evaluations; core.py: context bounds`. Trace the relevant arguments and return values before editing.

Wrap repeated toy reads with ReadCache. Increment state_version when the toy file or synthetic observation changes. Compare a baseline loader count with the cached count, then rerun task outcome and permission checks.

Create `tests/learner/test_lesson_25.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Use an explicit state version; do not cache effect verification.

```python
def read_version(cache, scope, version, loader):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 25's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 25 --scenario coding
python -m course_harness checkpoint 25 --scenario sre
python -m course_harness checkpoint 25 --scenario automation
pytest -q tests -k lesson_25
pytest -q tests/learner/test_lesson_25.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
two reads with coding/file/v1/config1 -> loader called once
state changes to v2 -> loader called again
verification request -> bypass cache and observe actual state
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Try operation='write' or verify_effect=True. Both raise BoundaryError before loader invocation. Reusing v1 after a file change would be a caller bug; version discipline is part of correctness, not automatic magic.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Add a test proving a changed state or config version reloads the observation. Mutate a returned dictionary and show the next cache result is unchanged. Report saved reads alongside unchanged task/safety outcomes.

1. Count loader calls in a list or closure.
2. Use a separate explicit version string rather than just a path.
3. A cached health fact cannot prove a restart succeeded.

## Acceptance checks

Baseline and candidate use comparable fixtures; required outcomes and gates remain intact; state/config changes miss the cache; returned values do not mutate shared entries; side effects and effect verification are rejected.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/25.md).

## Explain before continuing

Which assumptions make a cache valid? Why is a faster unsafe run not an optimization?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 25 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Add selective memory retrieval or bounded batching, then compare across several fixture cases instead of one successful timing.
