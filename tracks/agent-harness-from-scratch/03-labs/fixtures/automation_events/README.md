# Synthetic admission events

`events.json` covers the same coding, SRE, and automation paths. The repeated
automation key is intentional: admission returns the existing task identifier.
There are no real notifications, repository executors, services, or network calls.

Deduplication lasts for this SQLite database's lifetime. Queue capacity counts
queued, running, and uncertain work. Completed/dead-letter history remains
inspectable and is not pruned; this teaching implementation is not bounded disk
retention. Overflow rejects the incoming event so its source can explicitly retry.

Action recovery requires exclusive startup. Expired queue leases become uncertain;
an operator observes the fixture's actual state and reconciles a result instead of
blindly repeating the callback. `SafeRetry` is an explicit declaration that a
retry is safe, not automatic inference from an exception.

Schedules use fixed UTC elapsed intervals and timezone labels. They support one
latest catch-up or skipping missed intervals, with skip/queue overlap policies.
They do not implement civil-time cron or promise 9am through DST transitions.
Wall timestamps survive restart; actual tool timeout budgets need a monotonic
clock. System clock jumps can delay or expire leases and need operator inspection.

The worker is cooperative: a callback must inspect cancellation/human stop before
each new effect. It cannot terminate a hung callback; forced process limits and
stronger isolation are separate executor exercises. Heartbeats report stale work;
they do not automatically restart workers or clear stop/uncertainty.

## Operator sequence

Inspect `queue.inspect()` and `queue.health()` before changing state. Use
`queue.pause()` to stop admission and claiming; use `queue.drain()` to reject new
events while accepted work finishes. A drain does not clear an existing pause.
`queue.stop()` records a human stop that survives reopening the database.
`queue.cancel(task_id)` prevents queued work from running and flags an active
callback to stop before its next action. Operators explicitly invoke
`queue.resume(clear_human_stop=True)` to clear the human stop after inspecting
unresolved work; ordinary resume never clears it.

On exclusive startup call `store.recover()` to expose interrupted actions. Call
`queue.recover()` for expired worker leases. Inspect actual fixture state and call
`reconcile(..., observed=True)` with the observation receipt. This records what
happened; it never repeats an effect. If a retry is desired after observing no
effect, enqueue a new, explicitly scoped event key rather than altering the old
receipt. `queue.restart_permitted(limit=2)` consumes a durable supervisor restart
budget and refuses stop, pause, drain, active, or unresolved states. It does not
launch a process. Exhausted safe retries enter `dead_letter`, visible in inspect.

Run the fixture checkpoint through the lesson CLI or call
`course_harness.resident.checkpoint(14, "automation")`. Its checks raise on failure
and its trace comes from actual SQLite journal events. Required validation is
`pytest tests/integration/test_resident.py`; this command was not run on the
source-only authoring Mac. Named-zone DST tests need a system timezone database
(or the `tzdata` development dependency on Windows).
