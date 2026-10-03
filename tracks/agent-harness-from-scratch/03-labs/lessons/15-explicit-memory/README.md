# Lesson 15: Explicit memory and retention

Prerequisite: Lesson 14; M5. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Keep durable task state in the action store. Put only deliberately selected cross-run facts into MemoryStore. Each record has scope, key, revision, value, source, creation time and expiry. Read the latest revision before checking expiry so an expired correction cannot resurrect an older fact. Retrieved rows remain untrusted evidence.

## Diagram and text equivalent

```text
observation -> explicit selection -> scoped revision -> retrieval -> context
```

A caller selects a fact, records its origin and expiry, then retrieves the latest scoped revision as evidence for later context.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: MemoryStore.put, inspect, retrieve, delete and prune`. Trace the relevant arguments and return values before editing.

In your learner branch, add a small remember_fact helper that chooses a scope and requires an explicit public classification. Return the stored revision, not an assertion that the fact is true. Keep host policy separate.

Create `tests/learner/test_lesson_15.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Return the new revision; do not change host policy.

```python
def remember_fact(memory, scope, key, value, source):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 15's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 15 --scenario coding
python -m course_harness checkpoint 15 --scenario sre
python -m course_harness checkpoint 15 --scenario automation
pytest -q tests -k lesson_15
pytest -q tests/learner/test_lesson_15.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
put(scope='coding', key='style') -> revision=1
correct same key -> revision=2
retrieve coding -> latest revision, trust=untrusted-memory
delete -> no later retrieval
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Save a long-lived revision and then a short-lived correction. Move an injected clock past the correction's expiry. Retrieval must return no fact, rather than the old revision. Inspection should still explain both revisions until prune/delete.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Save 'use spaces' for the toy coding project, 'health fixture is synthetic' for the toy service, and 'ask before artifact replacement' for automation. Correct the coding fact, delete the automation preference, and write a test that another scope cannot retrieve the coding convention.

1. Use a mutable list as your clock: clock=lambda: now[0].
2. Use different scope strings, not one global bucket.
3. Query inspect before and after deleting; deletion removes correction history too.

## Acceptance checks

A current fact is returned only in its scope; the newest correction wins; stale corrections do not revive older values; delete stops retrieval; explicit secret classification and known-secret fixtures are rejected.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/15.md).

## Explain before continuing

Why is a memory record not a permission grant? Explain why the newest record may be unavailable even when an older record has a later expiry.

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 15 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Add a text search index only after comparing it to the small case-insensitive query; preserve scope and expiry checks.
