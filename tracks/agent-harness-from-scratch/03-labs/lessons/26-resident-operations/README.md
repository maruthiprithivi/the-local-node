# Lesson 26: Resident operations and graceful degradation

Prerequisite: Lessons 14, 20, 23 and 25; M7. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Separate persisted UTC schedule slots from monotonic execution deadlines. Schedule supports elapsed intervals with timezone presentation, not civil-time cron. missed='latest' admits at most one catch-up; missed='skip' discards gaps. overlap='skip' avoids concurrent logical jobs; overlap='queue' still obeys capacity. Provider outages remain on the configured destination.

## Diagram and text equivalent

```text
schedule slot -> overlap/missed policy -> bounded queue; operator stop -> persisted admission gate
```

Scheduling computes a UTC slot and applies documented catch-up and overlap decisions before admission. Operator controls persist in the store.

## Read, then make the smallest change

Open [resident.py](../../src/course_harness/resident.py) and follow the named APIs.

Read `resident.py: Schedule.admit, ResidentQueue.pause/drain/stop/resume/health/recover; persistence.py control state`. Trace the relevant arguments and return values before editing.

Add an operator helper that first prints health/inspect, then offers pause, drain, stop or explicit human-stop reset. Keep reconciliation separate. Simulate a schedule gap with an aware datetime; do not wait for a real outage.

Create `tests/learner/test_lesson_26.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Inspect and persist stop; do not clear unresolved work or implicitly resume.

```python
def operator_stop(queue):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 26's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 26 --scenario coding
python -m course_harness checkpoint 26 --scenario sre
python -m course_harness checkpoint 26 --scenario automation
pytest -q tests -k lesson_26
pytest -q tests/learner/test_lesson_26.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
downtime across 5 slots; latest -> one newest task
pause -> no claim/admission
drain -> no new admission, accepted work can finish
stop -> persistent human_stop; resume without reset rejected
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Expire a worker lease, call recover and reopen the store. The task stays uncertain. resume cannot declare its effect absent or clear stop implicitly. Cooperative callbacks need explicit stop checks; there is no real process watchdog that can kill them.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Test latest versus skip catch-up, overlap rejection and stop across restart. Write a four-step runbook: inspect, stop, observe/reconcile uncertain effects, explicitly resume. Include a provider outage escalation, never an implicit hosted fallback.

1. Use timezone-aware datetime values and an injected store clock.
2. Schedule interval is elapsed seconds; local display may shift across DST.
3. clear_human_stop=True is an explicit operator act, never a model suggestion.

## Acceptance checks

At most one latest catch-up occurs; overlap/capacity policies hold; pause/drain/stop differ as documented; outages do not create retry storms; recovery retains stop and uncertainty; backlog remains inspectable.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/26.md).

## Explain before continuing

Why use monotonic time for a deadline but persisted wall time for a future schedule? Which behavior is deliberately unsupported by this interval scheduler?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 26 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Add civil-time schedules with explicit DST ambiguity/nonexistence rules and timezone database fixtures before promising '9am daily'.
