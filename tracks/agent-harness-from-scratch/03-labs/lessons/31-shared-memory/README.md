# Lesson 31: Multiple users and central memory

Prerequisites: Lessons 6, 13 and 15. This extends the same engine after the core course;
there is no new final project. Work from `03-labs/` after setup. Complete this
lesson in three small sessions: trace the boundary, implement/test the delta,
then explain the outcome. Required work remains offline.

## What we build and why

Two simulated authenticated users share selected facts through one local service boundary. Personal scope belongs to the authenticated caller. Publishing requires an explicit owner choice and authorized team membership. Check access before retrieval reaches a provider. Retain owner, provenance, expiry and version; optimistic edits surface conflict. Revocation blocks future access and deletion invalidates published descendants.

## Diagram and text equivalent

```text
verified user -> ACL/scope -> private memory -> explicit selected publication -> team retrieval
```

The service verifies the caller and scope before touching content. An owner explicitly publishes one record; other private records remain unavailable.

## Read and implement one delta

Open [team.py](../../src/course_harness/team.py) and inspect
`Authenticator.authenticate/verify; TeamBoundary put_memory/read_memory/inspect_memory/publish_memory/delete_memory; host membership administration`. Keep the controller, policy and store ownership visible.
Read [the extension guide](../../../02-lab-book/advanced-extensions.md).

Create `tests/learner/test_lesson_31.py` and start with this helper:

```python
def share_selected(boundary, owner, memory_id, team_id, *, consent):
    # TODO: Use publish_memory and preserve its explicit consent argument; never publish a full transcript by default.
    raise NotImplementedError("Complete the learner boundary")
```

Write a successful assertion and an edge case before filling the TODO. Use
synthetic inputs and inspect effect counts; do not replace host authorization
with model confidence. [Separate solution](../../solutions/31.md).

## Commands and expected evidence

```sh
python -m course_harness checkpoint 31 --scenario coding
python -m course_harness checkpoint 31 --scenario sre
python -m course_harness checkpoint 31 --scenario automation
pytest -q tests/integration/test_team.py
pytest -q tests/learner/test_lesson_31.py
```

Expected: checkpoint JSON identifies the lesson/scenario and contains true
boundary checks plus a finite stop reason. Tests should select and execute useful
checks, not report zero selection. The final command exists after you author the
learner test. These are execution instructions, not a claim of a passing run on
the source-only Mac. Check current remote validation evidence in the track README.

## Readable successful trace

```text
A authenticated -> private convention + private preference
A consents to convention publication -> team version1
B reads team convention; B cannot inspect A private preference
B stale expected_version -> conflict, no overwrite
membership revoked -> future read rejected; delete origin -> shared descendant absent
```

The trace describes semantic order. Look for corresponding IDs, decisions and
receipts in actual output; fixture/helper events need not use these literal names.
Coding uses disposable files, SRE uses synthetic observations and automation uses
local fixture events throughout this extension.

## Controlled failure

Construct AuthContext('alice', permissions) directly instead of using Authenticator.authenticate. The boundary rejects it. Write the same shared key with expected_version=0 after version1 exists: reject conflict. Revoke B's membership and verify future access fails even if B saw the earlier value.

Predict the permitted effect count and durable state before replaying the fault.
Keep failed input separate from the reference fixture and restore it afterward.

## Exercise and progressive hints

User A shares a toy project convention with B while retaining a private preference. B proposes a conflicting correction; inspect version history, reconcile explicitly, revoke B and delete the original. Add read/search/write/delete leakage tests and a cached-deletion case.

1. Tokens map to identity in the fixture authenticator; arbitrary JSON usernames are never callers.
2. Use scope='user' for private data and publish_memory(..., consent=True) for selected sharing.
3. expected_version binds a write to the record observed; a conflict requires inspection, not blind retry.

## Automated acceptance checks

Forged contexts fail; user/team/project/task scopes enforce ACLs before model context; selected consented publication is attributable; stale edits conflict; revocation applies to future access; deletion/retention do not resurrect published/indexed values.

Reference integration checks cover the delivered mechanism; your test verifies
your own incremental delta. Remove the guard once to prove your test detects the
regression, then restore it. Mark missing live integration, actual authentication,
process isolation or multi-host behavior explicitly rather than inferring it from
an offline fixture pass.

## Self-check and plain explanation

Why is prompt-only filtering too late? What does revocation protect, and which information cannot be recalled after disclosure?

Explain the input, the trusted host decision, the untrusted evidence and the
resulting stop/recovery state. A simulated identity, check receipt or reviewer is
useful for a deterministic exercise; it is not proof of a production boundary.

## Checkpoint and optional continuation

Re-run checkpoint 31 to inspect the reference mechanism without overwriting
your learner branch. Preserve your diff before experimenting.

Add a real authenticated service interface in a separately hardened environment. A SQLite file is not a distributed central memory service and must not be shared across hosts.

