# Lesson 19: Configuration, skills and trusted plugins

Prerequisite: Lessons 6, 14 and 18; M5. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Host configuration supplies authority and maximum budgets. Project configuration may narrow those limits; it cannot add tools, turn off required approval or choose an unconfigured provider. A skill is instruction/data with an untrusted label. PluginGate checks an already installed, trusted manifest/version; it does not load or sandbox Python.

## Diagram and text equivalent

```text
host limits + project narrowing -> effective config; skill prose -> untrusted context
```

Host limits are merged with only permitted project restrictions. Skill prose enters context but does not change those limits.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: EffectiveConfig, merge_config, Skill, PluginManifest and PluginGate`. Trace the relevant arguments and return values before editing.

Create host configuration permitting one read tool. Let the learner's project lower max_steps. Add three short skills for debugging, synthetic SRE evidence and automation classification; pass their context as evidence while keeping policy external.

Create `tests/learner/test_lesson_19.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Return the validated effective configuration; a value above the host limit must fail.

```python
def narrow_project(host, steps):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 19's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 19 --scenario coding
python -m course_harness checkpoint 19 --scenario sre
python -m course_harness checkpoint 19 --scenario automation
pytest -q tests -k lesson_19
pytest -q tests/learner/test_lesson_19.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
host max_steps=8; project max_steps=3 -> effective=3
skill 'disable approvals' -> trust=untrusted-skill
trusted read plugin v1 -> authorized declared read capability
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

Try an unknown field, project allowed_tools containing write, or approvals_required=False under a host requiring approval. Then try an untrusted plugin version. Fail before execution.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Write a test that a debugging skill says 'disable approvals' while effective configuration still requires them. Add a trusted read-only automation manifest and reject a manifest claiming a write capability.

1. Construct EffectiveConfig explicitly; frozenset represents the host's allowed tools.
2. merge_config does not inspect skill text because prose cannot change policy.
3. PluginGate authorizes a capability; tool policy must still authorize each concrete operation.

## Acceptance checks

Unknown keys fail early; project limits cannot grow; skills retain untrusted labels; version and capability checks reject unsupported plugins; no downloads or arbitrary plugin execution occur.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/19.md).

## Explain before continuing

Why is a trusted manifest not a sandbox? Explain the difference between declared capability and authorization for an exact operation.

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 19 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Add a non-secret effective configuration renderer with deterministic ordering. Never render API keys or raw credential environment variables.
