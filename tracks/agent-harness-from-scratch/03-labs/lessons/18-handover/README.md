# Lesson 18: Model switching and constrained handover

Prerequisite: Lessons 13, 16 and 17; M5. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

A handover packet records goal, evidence, changes, completed and pending action IDs, uncertainty, permissions, required capabilities and remaining steps. The host chooses destinations and data localities. Validation creates an auditable switch record; it does not contact a provider or resume actions by itself.

## Diagram and text equivalent

```text
interrupted run -> evidence packet -> host destination/capability gate -> receiver
```

The first run packages evidence and remaining constraints. Host validation checks the receiver before continuation.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: Handover and validate_handover; persistence.py completed/uncertain actions`. Trace the relevant arguments and return values before editing.

Construct a packet after the toy coding read or SRE observation. Validate a switch between two fake-local destinations, then give the receiver only recorded results and pending work. Reuse the durable action store rather than re-running completed effects.

Create `tests/learner/test_lesson_18.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Use the host's two configured local destinations; preserve remaining authority and budget.

```python
def switch_locally(packet, destination):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 18's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 18 --scenario coding
python -m course_harness checkpoint 18 --scenario sre
python -m course_harness checkpoint 18 --scenario automation
pytest -q tests -k lesson_18
pytest -q tests/learner/test_lesson_18.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
goal + completed={read-1} + pending={diagnose-2}
destination fake-b configured; local; read-only; steps <= remaining
switch record -> trust=untrusted-handover
receiver continues pending work only
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Attempt local-to-hosted fallback without approved hosted locality, add receiver permissions, or increase remaining steps. Each change must raise BoundaryError. A provider outage cannot silently become consent to export content.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Build three packets for coding, SRE and automation. For each, preserve one completed ID and one uncertainty. Write a test proving that a completed action cannot also appear as pending.

1. Start with no pending side effect and narrow receiver permissions.
2. Receiver permissions may be a subset of the original permissions.
3. The switch reason is required even for fake-local changes.

## Acceptance checks

Configured destinations and capabilities are required; budget and authority cannot expand; completed IDs never re-enter pending; locality and credential readiness are explicit; every accepted switch records its reason.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/18.md).

## Explain before continuing

Which facts are evidence and which values are host constraints? Why must a model-provided handover be revalidated?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 18 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Connect a validated packet to Engine using durable results, then test an interrupted run without repeating its mutation.
