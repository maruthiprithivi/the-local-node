# Lesson 14: A resident harness: triggers, queue, and lifecycle

Lesson 13. Read [setup](../../../02-lab-book/setup.md) before running commands.

## What we are building

Drive bounded runs from durable local events while preserving stop and recovery semantics. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Picture the flow

```text
local event/schedule → bounded durable queue → leased worker → Engine.run → result/dead letter
```

Text equivalent: local event/schedule passes into bounded durable queue passes into leased worker passes into Engine.run passes into result/dead letter. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

## Read first, then make one small change

Read [the implementation](../../src/course_harness/resident.py) and locate `ResidentQueue`, `ResidentWorker.tick`, queue admission/claim, lifecycle controls, and persisted human stop. Read the underlying `DurableStore` in [persistence.py](../../src/course_harness/persistence.py). Trace the successful path before editing.

Keep trigger parsing and queue management outside prompts. Give events stable deduplication keys within a documented scope. Admit only within capacity; reject, delay, or coalesce according to an explicit rule. A single worker claims work with a lease; lease expiry recovers ownership, not proof of zero effects. Add retry-ready time and dead-letter state. Startup recovers state, shutdown stops admission and drains or records work within a bound. Persist human stop so a process restart cannot erase operator intent.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

## Minimal code to inspect and extend

Queue admission owns capacity/deduplication; worker callback runs the existing engine. Human stop persists in the same store.

```python
from tempfile import TemporaryDirectory
from pathlib import Path
from course_harness.persistence import DurableStore
from course_harness.resident import ResidentQueue
with TemporaryDirectory() as root:
    store = DurableStore(Path(root) / "queue.sqlite", clock=lambda: 100)
    queue = ResidentQueue(store, capacity=1)
    first = queue.enqueue("event-1", {"scenario": "coding"})
    assert queue.enqueue("event-1", {"scenario": "coding"}) == first
    queue.stop()
    assert queue.claim("worker-1") is None
    store.close()
```

Concrete exercise delta: Extend the event source, not the prompt, to add fake-clock schedule ticks. The delivered queue rejects overflow and retains dedup keys for the database lifetime (no pruning); completed/dead tasks do not count toward active capacity, but stored history grows. Test expired leases and uncertain effects separately. Lifecycle tests must reopen the store to prove stop durability.

The complete test fragment lives in the separate solution. Keep your new helper/test on your learning branch; baseline checkpoints remain available while you work.

## Run a checkpoint

From `tracks/agent-harness-from-scratch/03-labs`, with the environment installed as in setup:

```sh
python -m course_harness checkpoint 14 --scenario coding
python -m course_harness checkpoint 14 --scenario sre
python -m course_harness checkpoint 14 --scenario automation
pytest -q tests -k lesson_14
```

These are learner/approved-worker commands. Do not execute them on the source-only authoring Mac. Expected CLI output is JSON with `lesson`, `scenario`, `status`, `stop_reason`, `trace`, and `checks`. Inspect the check values and exit status; absence of selected tests is not a pass.

Logical duplicates produce one admitted task within scope; overflow is visible; shutdown/restart preserve work and human stop; unresolved effects are inspectable. The walkthrough below explains meaningful event order; helper/fixture events may be represented inside check records rather than as literal CLI event names.

Exact baseline expectation: Expected resident events include `task.admitted`, `task.claimed`, `task.completed`, `task.uncertain`, `task.reconciled`, and `resident.human_stop`; the shared engine adds its model/tool/stop events. Inspect `shared_engine` and `no_effects` checks. The checkpoint stops as `checkpoint_passed`.

## Read a successful trace

```text
event_admitted -> duplicate_ignored -> task_claimed -> run_started -> run_stopped -> task_completed; human_stop -> restart_stopped
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

## Break it on purpose

Create an event storm and a crashed claimed task. Capacity must remain bounded. Restart after human stop must claim/execute no new work even if the queue still contains tasks.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

## Your exercise

Feed duplicate events, overflow admission, expire a claim, and request human stop. Restart the supervisor and inspect retained queue/action state. Send one coding, one SRE, and one automation event through the same engine. Resolve an uncertain action before making its task eligible again.

Before opening the solution, write one learner test in a separate `test_learner_14.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Use database state, not a process-local set, for deduplication.
2. Test ownership recovery separately from effect reconciliation.
3. A stop flag controls admission/dispatch; it does not erase the backlog.

[Reference solution and test reasoning](../../solutions/14.md). Try the first hint and your own test before reading it.

## Acceptance checks

Scoped deduplication; capacity/backpressure; claim recovery; bounded retries/dead letters; graceful/forced-stop recording; stop survives restart; three scenarios. Add a duplicate arriving after restart.

The selected delivered checks are a baseline. Your extra test should fail when your exercise change is removed and pass when it is restored. Use controlled fixtures and injected time; required checks need no network or real infrastructure. Record unimplemented or unvalidated assertions honestly.

## Explain it back

What does a lease establish? When is coalescing inappropriate? Why must the watchdog honor human stop?

Plain-language explanation: A resident harness is ordinary lifecycle and queue code around the same bounded controller. The model does not schedule, own leases, or override stop controls.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Optional next extension

Add a fake-clock scheduled trigger and explicitly choose whether missed runs are skipped or caught up once.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
