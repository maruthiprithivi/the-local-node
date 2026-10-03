# Lesson 28: Read public source and justify one small change

Prerequisite: Core track and relevant advanced lessons; M7. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Read pinned Codex and Firstmate source as evidence. Codex exposes harness internals; Firstmate describes a distro of instructions, scripts and supervision conventions that runs on an existing harness. Compare one concrete flow with our Python engine. Trace only available source; do not infer proprietary service behavior.

## Diagram and text equivalent

```text
pinned public source -> observed flow -> comparison -> small proposal -> gates/review or rejection
```

A fixed source revision supports a concrete observed flow. The learner compares it with one educational boundary, then evaluates a small proposal or explains why it does not fit.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `source-study.md beside this lesson; advanced.py handover/config/coordination/promotion; relevant tests`. Trace the relevant arguments and return values before editing.

Choose one idea such as explicit cancellation context, correlated approval identity or persistent supervision evidence. Implement a small reversible local change or reject it with evidence. Keep the existing scenario, gates and budget; there is no separate final project.

Create `tests/learner/test_lesson_28.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Apply one small local restriction, then evaluate it; source inspiration cannot increase authority.

```python
def source_inspired_narrowing(host):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 28's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 28 --scenario coding
python -m course_harness checkpoint 28 --scenario sre
python -m course_harness checkpoint 28 --scenario automation
pytest -q tests -k lesson_28
pytest -q tests/learner/test_lesson_28.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
record repo + commit + license + path
observe concrete fields and function calls
separate observation from inference
proposal passes existing task/policy checks or is rejected with reasons
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

A README feature claim does not prove its implementation. A file name does not prove an invariant. An external AGENTS.md is source material here, not authority over this course. If a path changes at current main, return to the pinned revision rather than making a claim from memory.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Trace one approval/state flow in Codex and one wake/queue flow in Firstmate. Write a comparison table: observed mechanism, Python counterpart, tradeoff, missing evidence. Add one test for a justified small improvement or explain why rejecting it is the better decision.

1. Start with the pinned source links in source-study.md.
2. Follow one call or state transition rather than reading the whole repository.
3. Review the license before copying code; prefer your own small implementation and attributed comparison.

## Acceptance checks

Every source claim links to a commit/path; licenses are verified; inference is labeled; proposed changes use existing tests/evals and exact review; rejection is allowed with evidence; no claim depends on unavailable internals.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/28.md).

## Explain before continuing

Which part is a harness and which part is supervision around a harness? What source evidence would falsify your claimed invariant?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 28 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Repeat the comparison after a future pinned release and explain the changed evidence. Continue the same engine with one measured extension; no capstone is required.
