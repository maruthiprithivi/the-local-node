# Lesson 22: Task outcomes and regression evidence

Prerequisite: Lessons 20 and 21; M6. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

A code test says a component followed its contract. A task evaluation asks whether the goal was achieved safely. Record task ID, scenario, development/held-out split, executable outcome, unsafe attempts, steps, latency, usage and config/fixture versions. Held-out tasks are withheld during tuning; do not tune on their failures repeatedly.

## Diagram and text equivalent

```text
versioned tasks -> run + executable outcome -> metrics -> per-task comparison
```

Versioned tasks produce outcomes and measurements, then a comparison checks individual regressions alongside totals.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: Evaluation, evaluate and compare_evaluations; evals fixtures`. Trace the relevant arguments and return values before editing.

Add one denied or impossible task to the held-out fixtures. Its correct result may be a refusal or escalation, not completion. Compare baseline and candidate over the same task/split/fixture identities.

Create `tests/learner/test_lesson_22.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Count executable outcomes only when unsafe_attempts is zero.

```python
def safe_successes(records):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 22's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 22 --scenario coding
python -m course_harness checkpoint 22 --scenario sre
python -m course_harness checkpoint 22 --scenario automation
pytest -q tests -k lesson_22
pytest -q tests/learner/test_lesson_22.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
baseline safe successes=3
candidate safe successes=3; fewer steps
same task/split/fixture IDs -> comparable
unsafe_attempts=0 -> candidate may be acceptable
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Make a candidate faster but introduce one unsafe attempt. evaluate must exclude that completion from successes; compare_evaluations must reject it even if aggregate latency improves.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Create coding, SRE and automation Evaluation records. Change one outcome from true to false and verify the task ID appears in regressions. Add a test proving mismatched fixture versions cannot be compared.

1. Use dataclasses.replace to construct candidates without mutating the baseline.
2. Boolean outcome comes from an executable fixture check, not model self-rating.
3. Unknown usage across any row makes aggregate usage unknown.

## Acceptance checks

Same fixtures are required; fake records reproduce; unsafe completion is not success; a per-task regression is detected; sample size and usage uncertainty are visible.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/22.md).

## Explain before continuing

Why can't a higher average success rate excuse a new permission failure? Explain how a held-out case differs from a unit test.

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 22 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Compare two bounded context strategies across multiple fixture versions. Report sample size, tradeoffs and limits; fake evaluations do not establish live-model quality.
