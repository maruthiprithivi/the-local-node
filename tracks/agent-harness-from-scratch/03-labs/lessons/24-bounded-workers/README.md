# Lesson 24: Two workers and one global budget

Prerequisite: Lessons 18, 20 and 23; M7. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Start with two trusted cooperative read-only workers. Each has a stable ID and explicit scope. Admission caps tasks and concurrency; one locked shared budget pays for worker admission and observations. Results are structured untrusted evidence. Recursive coordination and mutations are denied. Threads share memory; they are not isolation.

## Diagram and text equivalent

```text
coordinator -> shared budget -> worker A/read scope A + worker B/read scope B -> results
```

A coordinator admits at most two concurrent workers, who consume one shared budget and return scoped observations.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: WorkerTask, WorkerContext.read, SharedBudget, coordinate and merge_worker_findings`. Trace the relevant arguments and return values before editing.

Create two inspection tasks for independent toy files, two synthetic evidence sources, or two automation classifications. Each worker must call context.read using its assigned scope. Return evidence to the coordinator; do not apply a worker-proposed mutation.

Create `tests/learner/test_lesson_24.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Two admissions plus two reads fit four shared units. Do not authorize mutations in a worker.

```python
def inspect_two(tasks, observe):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 24's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 24 --scenario coding
python -m course_harness checkpoint 24 --scenario sre
python -m course_harness checkpoint 24 --scenario automation
pytest -q tests -k lesson_24
pytest -q tests/learner/test_lesson_24.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
admit worker A + worker B -> 2 budget units
one read each -> 2 more units
results stable input order; trust=untrusted-worker
coordinator decides later actions through ordinary policy
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Give both workers a dictionary with the same finding key and different values.
`merge_worker_findings` removes the key from accepted findings and records both
values in `conflicts`; it does not choose the confident worker or merge writes.
Add a test that conflicting evidence remains visible for coordinator review.

Ask a worker to read another scope or recursively call coordinate. Its result is failed, not silently dropped. Set cancellation before admission and verify no observation callback runs. Allocation between concurrent workers may vary; test total limits, not a scheduling race.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Write a worker that attempts the wrong scope, then prove failures remain visible. Compare two workers with sequential reads: record useful units and overhead rather than assuming parallel is always faster.

1. Each worker admission costs one unit before its context.read call.
2. Pass threading.Event for cooperative cancellation.
3. The callback is trusted host code; a malicious callable could bypass these helper methods.

## Acceptance checks

At most two workers run; total budget is enforced under a lock; cancellation prevents new observations; recursive spawn and write operations are rejected; scopes and failures are visible; workers cannot grant authority.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/24.md).

## Explain before continuing

When is sequential work simpler? Why can't Python threads forcibly stop a hung tool or enforce a malicious callable's scope?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 24 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Add process isolation with explicit IPC and cleanup in an approved environment, retaining the same policy and budget contracts.
