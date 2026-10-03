# Lesson 30: A GitHub mention becomes bounded draft work

Prerequisites: Lessons 7, 13, 14 and 20. This extends the same engine after the core course;
there is no new final project. Work from `03-labs/` after setup. Complete this
lesson in three small sessions: trace the boundary, implement/test the delta,
then explain the outcome. Required work remains offline.

## What we build and why

Replay @course-harness against FakeGitHub and a durable queue. Verify the raw-body HMAC fixture signature before JSON parsing; obtain actor/comment data from the fresh fake API record. Gate repository, fork, command, permission and exact base. Produce one isolated fake branch/diff, synthetic check receipt and exact publication approval before a fake draft PR. No live webhook, app, secret or paid call is created.

## Diagram and text equivalent

```text
signed event -> fresh authorization -> exact parser -> durable task -> toy diff/check -> approval -> fake draft receipt
```

Authentication precedes command parsing. One bounded durable task produces reviewable evidence. Publication is a separate exact approved action and never a merge.

## Read and implement one delta

Open [extensions.py](../../src/course_harness/extensions.py) and inspect
`MentionReceiver.receive/prepare_next/publication_digest/publish/reconcile_publication; FakeGitHub; examples/github/`. Keep the controller, policy and store ownership visible.
Read [the extension guide](../../../02-lab-book/advanced-extensions.md).

Create `tests/learner/test_lesson_30.py` and start with this helper:

```python
def replay_fixture(receiver, event):
    # TODO: Serialize the synthetic sender's event and call receive with its fixture signature. Do not pass an actor ID in JSON.
    raise NotImplementedError("Complete the learner boundary")
```

Write a successful assertion and an edge case before filling the TODO. Use
synthetic inputs and inspect effect counts; do not replace host authorization
with model confidence. [Separate solution](../../solutions/30.md).

## Commands and expected evidence

```sh
python -m course_harness checkpoint 30 --scenario coding
python -m course_harness checkpoint 30 --scenario sre
python -m course_harness checkpoint 30 --scenario automation
pytest -q tests/integration/test_extensions.py
pytest -q tests/learner/test_lesson_30.py
```

Expected: checkpoint JSON identifies the lesson/scenario and contains true
boundary checks plus a finite stop reason. Tests should select and execute useful
checks, not report zero selection. The final command exists after you author the
learner test. These are execution instructions, not a claim of a passing run on
the source-only Mac. Check current remote validation evidence in the track README.

## Readable successful trace

```text
signed permitted fix -> admitted task_id=1
redelivery -> duplicate task_id=1
prepare_next -> fake_branch_diff + synthetic_check_receipt + digest
publish exact fresh approval -> one fake draft PR, merged=False
lost acknowledgment -> uncertain -> find existing PR -> reconcile
```

The trace describes semantic order. Look for corresponding IDs, decisions and
receipts in actual output; fixture/helper events need not use these literal names.
Coding uses disposable files, SRE uses synthetic observations and automation uses
local fixture events throughout this extension.

## Controlled failure

Set the fresh fake actor's permission to read, use a fork or stale base, or mutate the signed body. No task should enter privileged work. Then simulate ambiguous_publish=True: one fake PR exists, task becomes uncertain, and reconcile_publication discovers it instead of creating another.

Predict the permitted effect count and durable state before replaying the fault.
Keep failed input separate from the reference fixture and restore it afterward.

## Exercise and progressive hints

Replay one bug-fix event twice, inspect the bounded diff/check receipt, and publish only after reviewing its exact digest in the fixture. Replay an unauthorized mention. Add changed/deleted comment, access revocation, cancel, expired approval, stale base, bot-loop and rate-limit cases; report any unsupported live behavior.

1. The event contract contains repository/comment_id/revision/base/fork/action; actor comes from client.comment.
2. receiver.sign exists only for the synthetic sender exercise; never expose it on a real receiver.
3. After a possible create effect, inspect find_pr by stable dedup key; a timeout is not proof of absence.

## Automated acceptance checks

The publication method is a trusted operator API in this fixture, never a
model-dispatched tool or a body-supplied approval field. A real receiver needs
authenticated operators and durable review receipts. The toy check verifies
synthetic postconditions via the shared Engine; it does not execute PR tests or
prove arbitrary checked-out code is safe to run.

Signature/actor/repository/fork/command gates precede work; one logical delivery creates one task/receipt; cancelled or changed requests cannot publish; successful synthetic checks and exact fresh approval are required; ambiguous effects reconcile; no merges or live activation.

Reference integration checks cover the delivered mechanism; your test verifies
your own incremental delta. Remove the guard once to prove your test detects the
regression, then restore it. Mark missing live integration, actual authentication,
process isolation or multi-host behavior explicitly rather than inferring it from
an offline fixture pass.

## Self-check and plain explanation

Why isn't an @mention a permission grant? Which fixture value represents authentication, and what must replace it in a real deployment?

Explain the input, the trusted host decision, the untrusted evidence and the
resulting stop/recovery state. A simulated identity, check receipt or reviewer is
useful for a deterministic exercise; it is not proof of a production boundary.

## Checkpoint and optional continuation

Re-run checkpoint 30 to inspect the reference mechanism without overwriting
your learner branch. Preserve your diff before experimenting.

Study the actual Claude action and security guide linked in advanced-extensions.md. A separately reviewed live setup needs real auth, least-privilege grants, exact base trust and bounded spending. Inactive templates are examples only.

## Reviewed boundary clarification

The `plan` command performs a read-only controller run and stores a completed plan receipt. It creates no branch or PR and releases the worker immediately. Only `fix` prepares a disposable branch and waits for exact publication approval. Exercise a plan followed by a fix to prove the queue remains available.
