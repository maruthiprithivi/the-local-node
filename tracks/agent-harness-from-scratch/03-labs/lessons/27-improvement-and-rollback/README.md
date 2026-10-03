# Lesson 27: Controlled improvement and rollback

Prerequisite: Lessons 22, 23, 25 and 26; M7. Work from `03-labs/` after setup. Split this lesson into
three short sessions: read/trace, change/test, and explain/review. This is another
increment to the shared engine, not a separate project.

## Build and purpose

Treat a proposal as a versioned prompt/config artifact, separate from policy and gate definitions. Host-owned correctness, policy, adversarial and held-out gates produce a recommendation. Exact human review binds the artifact digest and gate evidence. Passing tests do not authorize promotion. Promotion and rollback affect local artifacts only, not a deployment.

## Diagram and text equivalent

```text
isolated proposal -> diff + host gates -> recommendation -> exact review -> version / rollback
```

A proposal passes independent gates, gets a recommendation, and becomes active only after review of its exact digest. The previous version remains available.

## Read, then make the smallest change

Open [advanced.py](../../src/course_harness/advanced.py) and follow the named APIs.

Read `advanced.py: PromotionStore.recommend, approve, promote, current and rollback`. Trace the relevant arguments and return values before editing.

On your learner branch propose a smaller bounded context setting for an existing scenario. Show the diff and collect real gate evidence. Store an accept/reject recommendation; exercise approval using a clearly labeled synthetic reviewer fixture, never a model-generated reviewer identity in a real host.

Create `tests/learner/test_lesson_27.py` on your branch for the exercise. Keep
solution reading separate until you have tried the first hint. Do not replace the
whole engine with the solution: compare only the boundary you are learning.

## Run the checkpoint

### Learner code delta

Add this function to your learner test file, then replace the TODO with the
smallest implementation using the named reference API. The starter deliberately
raises so an unfinished exercise cannot look complete. Create reviewable evidence without approving/promoting the artifact.

```python
def recommend_only(store, artifact, gates):
    # TODO: implement this boundary using the reference API.
    raise NotImplementedError("Complete lesson 27's learner delta")
```

Write a successful case and the lesson's edge case against this helper. The
separate solution shows the implementation after the hints; its test is a starting
point, and you must add the helper-specific assertions yourself.

## Checkpoint commands

```sh
python -m course_harness checkpoint 27 --scenario coding
python -m course_harness checkpoint 27 --scenario sre
python -m course_harness checkpoint 27 --scenario automation
pytest -q tests -k lesson_27
pytest -q tests/learner/test_lesson_27.py
```

The CLI prints structured offline checkpoint evidence tagged with lesson/scenario.
Exact JSON fields follow the implementation; inspect them alongside the semantic
trace below. Pytest should report selected checks passing, not merely zero tests.
The final command exists after you write your learner test. These are intended
learner commands, not an authoring test report; see the track's validation status.

## Successful path to inspect

```text
proposal passes all four gates -> accept, requires_review=True
promote before review -> rejected
fixture reviewer approves exact digest -> local version 2
rollback -> previous known-good artifact
```

This is a narrated semantic trace rather than a byte-for-byte CLI transcript.
Find the corresponding state/record in the checkpoint output. Across the three
paths, coding uses disposable files, SRE uses synthetic observations, and
automation uses fixture events. The same host gates continue to apply.

## Controlled failure

A faster proposal that disables approval fails the policy gate. Editing an approved artifact changes its digest and cannot reuse review. Missing or invented gates fail early. The proposer must not control the reviewer or gate results.

Run this fault only against your disposable learner fixtures. Predict the state
and effect count before running it; compare your prediction with the result.

## Exercise and progressive hints

Compare one useful context reduction with one unsafe speed shortcut. Write a test that modifying one character after approval blocks promotion, then a test that rollback restores the original artifact.

1. PromotionStore.GATES fixes the full gate set.
2. Pass an exact reviewed_digest from the human-facing diff artifact.
3. This classroom store assumes trusted host code calls approve; it is not user authentication.

## Acceptance checks

The shipped checkpoint uses scripted offline Engine outcomes and a synthetic
human-review fixture to demonstrate gate/promotion/rollback mechanics. It does
not establish live-model prompt quality or a beneficial real improvement.
Your proposal needs its own real fixture outcome evidence; a boolean gate
dictionary supplied by trusted test code is a mechanism demonstration.

Unsafe proposals reject; beneficial proposals wait for exact review; changed artifacts invalidate review; gate set cannot change; rollback restores the previous runnable config; no live deployment occurs.

The shipped checkpoint tests cover the reference path and an edge case. Your
learner test must assert a meaningful invariant and fail when that invariant is
removed. Run it alone, then with the suite; never claim a test passed from reading
its source. [Separate worked solution](../../solutions/27.md).

## Explain before continuing

What does a passing gate prove, and what does review authorize? Why must the same proposer not set its own passing safety evidence?

In plain language: identify the input, the host-owned boundary, the evidence that
crosses it, and the stop/recovery decision. A correct explanation plus a useful
new test demonstrates independence; copying a passing example demonstrates only
that you can follow it.

## Return point and optional extension

Re-run checkpoint 27 to return to a known reference demonstration without
changing your files. Preserve your own branch/diff before experimenting.

Bind actual evaluation artifact hashes and immutable reviewer receipts; separately design authentication before considering real multi-user promotion.
