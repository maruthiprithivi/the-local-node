# Lesson 32: Collaboration between separate harnesses

Prerequisites: lessons 18, 24, 26 and 31. Work from `03-labs/`. Keep the coding,
SRE and automation paths and their existing gates. This is another incremental
extension, with no separate final assignment.

## What we build and why

Agents inside one harness share a controller. Independently running harnesses
have separate provider, policy and executor boundaries. Define a versioned
TaskEnvelope with kind, correlation, principal, scope, capabilities, artifact
references, deadline, remaining budget, idempotency key and causal sequence.
TeamBoundary authenticates, deduplicates, bounds admission and records ownership
leases with increasing fencing tokens. A receiver checks its own permissions;
sender/model/worker prose cannot authorize an action.

The delivered exercise uses simulated local transport and host-minted identities.
It does not launch multiple processes or deploy a multi-host service. Leases and
fences protect this shared journal; an external side-effect service would also
need to enforce fencing. A fence cannot undo an already performed effect.

## Diagram and text equivalent

```text
coding harness -> scoped envelope -> coordinator/store -> SRE read lease
                 <- evidence/result receipt <-
automation follow-up -> local authorization/approval -> bounded action
expired lease -> uncertain + higher fence -> observe -> reconcile
```

Text equivalent: a coding instance requests scoped read-only SRE evidence through
the coordinator. The SRE receiver gets a bounded ownership lease and returns a
correlated receipt. Automation locally reauthorizes a follow-up. Expiry revokes
the journal owner's fence and creates uncertainty; observation precedes requeue
or completion.

## Read and make a concrete delta

Read [team.py](../../src/course_harness/team.py): TaskEnvelope, receive_task,
claim_task, receive_result, recover_tasks, reconcile_task and cancel_task. Inspect
the host-owned artifact-scope map and authenticated permission intersection.
Then read [the extension guide](../../../02-lab-book/advanced-extensions.md).

Create `tests/learner/test_lesson_32.py` with this starter:

```python
def claim_read_task(boundary, user, task_id):
    # TODO: claim with only observe_health and a five-second lease.
    raise NotImplementedError("Implement bounded receiver ownership")
```

Fill the TODO using claim_task. Add a positive claim and an expired-fence test.
Keep a receiver's concrete tool action routed through its ordinary Policy/Engine;
claiming a task is not approval to run every action in its payload.
[Separate solution](../../solutions/32.md).

## Commands and expected evidence

```sh
python -m course_harness checkpoint 32 --scenario coding
python -m course_harness checkpoint 32 --scenario sre
python -m course_harness checkpoint 32 --scenario automation
pytest -q tests/integration/test_team.py
pytest -q tests/learner/test_lesson_32.py
```

Expected: finite checkpoint JSON with all delivered boundary checks true and
correlated fixture trace; integration and learner tests execute selected checks.
These commands are for an approved execution host, not a passing authoring report.
No actual peer network or multi-process run is implied by a fixture checkpoint.

## Successful trace

```text
authenticated task envelope, sequence0 -> one task
identical redelivery -> existing task; conflicting redelivery -> reject
SRE receiver claim -> narrowed permissions, lease + fence
read-only evidence -> sequence1 result -> recorded receipt
lost acknowledgment -> identical result replay -> duplicate receipt
automation receives evidence -> local policy/approval decision
```

Semantic narration is distinct from literal CLI formatting. Use correlation and
task IDs to distinguish received evidence, owned work and completed effects.

## Controlled failures

Advance the injected clock beyond a worker lease. Recovery increments its fence
and marks work uncertain. The old worker cannot publish as current owner.
Observe whether its effect occurred; reconcile before requeue. Feed sequence2
before sequence1, a changed payload with the same idempotency key, a widened
capability set or a larger remaining budget: each must remain explicit failure.

Simulate a partition by withholding a receipt. Do not repeat a possible effect
just because no acknowledgment arrived. Cancellation prevents new work and
invalidates active ownership; it does not erase a completed effect. Host recovery
requires exclusive startup ownership and does not make memory into a lock.

## Exercise and hints

Have the coding harness request synthetic health evidence from an SRE harness,
then let automation propose an approved fixture follow-up. Use a handover between
two fake provider configurations; preserve locality, pending/completed IDs and
remaining steps from lesson 18. Replay duplicate and out-of-order events,
cancel a peer and expire a lease. Add one stale-writer test and one global
budget/fan-out test. Explicitly share only necessary artifacts/memory.

1. Authenticate each participant at the receiver boundary; do not trust the
   envelope's principal string by itself.
2. Compare the received capabilities with both task requirements and local host
   permissions. A delegate can narrow, never expand.
3. Fence journal writes and any external effect independently. Inspect uncertain
   state before deciding that requeue is safe.

## Automated acceptance checks

Duplicate deliveries do not duplicate logical work; sequence conflicts fail;
deadlines, remaining budget and fan-out stay bounded; stale owners cannot write
current receipts; lost acknowledgments reconcile; revoked membership and
cancelled tasks cannot grant authority. Conflicting edits remain visible.
Receivers enforce local action policy after envelope acceptance.

The default tests exercise deterministic single-host transport fixtures and
SQLite transactions. They do not establish distributed consensus, process
isolation, real identity verification or resilience of live peer networking.
Document these limits alongside any missing case; never equate a fixture pass
with production deployment readiness.

## Explain before continuing

How is shared memory different from a task lock? Why must the executor, not just
the journal, enforce a fencing token? Which observation makes a retry safe after
a lost acknowledgment? Explain why separate providers cannot broaden permissions
through a chain of handovers.

Plain explanation: a peer's request is evidence of desired work. The receiver
needs its own bounded authorization and current ownership before acting.

## Runnable return point and optional extension

Checkpoint 32 returns to the reference demonstration without resetting your work.
Preserve your own branch/diff. A later separately authorized extension can launch
two local processes with IPC and crash tests, then implement authenticated network
transport. Keep the same finite budgets, local policy and reconciliation rules.

