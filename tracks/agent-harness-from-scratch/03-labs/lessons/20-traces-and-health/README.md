# Lesson 20: Traces, usage and resident health

Prerequisite: Lesson 19; M5. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Correlate run, task, action and provider call IDs before calculating totals. Record attempts separately from successful calls and mark missing token usage unknown. Resident health exposes stop, pause, draining, pending/uncertain tasks and stale workers. Health is evidence, not permission to restart.

## Diagram and text equivalent

```text
run events + queue health + usage -> bounded redacted report -> diagnosis
```

The report joins already recorded evidence by stable identifiers and marks missing measurements rather than inventing them.

## Read, then make the smallest change

Open [observability.py](../../src/course_harness/observability.py) and follow the named APIs.

Read `observability.py: TraceSink.emit/redact and UsageLedger.record/estimate; core.py: RunResult; persistence.py: event records; resident.py: ResidentQueue.health/heartbeat`. Trace the relevant arguments and return values before editing.

Build a small report from the existing events and health dictionary. Add queue-age and approval-wait calculations only when both timestamps are present. Return None when evidence is absent. Use an injected clock; do not time sleep calls.

Create `tests/learner/test_lesson_20.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Only total validated provider usage when both counts are present.

```python
def known_total_usage(usage):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 20's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 20 --scenario coding
python -m course_harness checkpoint 20 --scenario sre
python -m course_harness checkpoint 20 --scenario automation
pytest -q tests -k lesson_20
pytest -q tests/learner/test_lesson_20.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
task admitted -> claimed -> action requested -> approved -> result -> completed
usage input known, output absent -> total unknown
health pending=0; uncertain=[]; human_stop=False
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Seed a request with missing usage and a stale lease. A report must not show zero cost or silently restart the worker. A watchdog cannot clear human stop or bypass uncertain effects. Inspect which timestamp justifies each duration.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Write an unknown-usage test and a fake-clock stale-worker test. Add one report row for each scenario showing its stop reason and evidence source. Diagnose queue wait separately from provider time.

1. Read Reply.usage keys, not a default zero.
2. ResidentQueue.health reports stale lease IDs without automatically recovering them.
3. Keep raw prompts and tool output out of service-level health summaries.

## Acceptance checks

Call/results correlate; retries are counted rather than hidden; unknown usage remains unknown; sensitive fixtures are redacted; fake-clock timings are deterministic; human stop and unresolved effects remain visible.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/20.md).

## Explain before continuing

Why does an empty usage dictionary mean unknown rather than free? Why is heartbeat liveness different from successful task progress?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 20 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Add configured price estimates with model/config version and uncertainty labels. Estimates are advisory; no paid experiment is needed.
