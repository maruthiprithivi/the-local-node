# Lesson 14: A resident harness: triggers, queue, and lifecycle: narration script

This is a readable recording script, not a published recording. It is adapted
from the canonical lesson text; keep that lab open for exact source snippets,
commands and separate solutions. Caption future recordings and describe arrows
and state changes aloud. The examples use synthetic fixtures and an offline fake
provider. Do not run demonstrations on the source-only authoring Mac.

## Opening and purpose

Drive bounded runs from durable local events while preserving stop and recovery semantics. Work in one growing `course_harness` package. The checkpoint selects cumulative behavior; it does not replace your source or wipe your exercise changes.

## Describe the diagram aloud

```text
local event/schedule → bounded durable queue → leased worker → Engine.run → result/dead letter
```

Text equivalent: local event/schedule passes into bounded durable queue passes into leased worker passes into Engine.run passes into result/dead letter. Read the flow from left to right; a branch represents a controller decision, not a command from untrusted text.

Read each arrow in order. Explain what enters the boundary, which trusted
component decides, and what evidence comes out. Pause before displaying code.

## Source walkthrough

Read [the implementation](../../src/course_harness/resident.py) and locate durable queue admission/claim, lifecycle controls, and persisted human stop. Trace the successful path before editing.

Keep trigger parsing and queue management outside prompts. Give events stable deduplication keys within a documented scope. Admit only within capacity; reject, delay, or coalesce according to an explicit rule. A single worker claims work with a lease; lease expiry recovers ownership, not proof of zero effects. Add retry-ready time and dead-letter state. Startup recovers state, shutdown stops admission and drains or records work within a bound. Persist human stop so a process restart cannot erase operator intent.

The continuing examples remain a disposable coding repository, synthetic SRE observations/service state, and local automation events/artifacts. Reuse the same engine rather than copying it into three domain-specific loops.

Open the lesson's minimal snippet. Narrate arguments, preconditions and return
values before typing the learner change. Keep the reference implementation intact
on its branch; learner tests should expose an unfinished TODO or missing guard.

## Demonstration and successful trace

Use the checkpoint commands from the lab on an approved execution host. Capture
actual terminal output; the following trace is a semantic narration, not a claim
that these exact event names are printed by every helper.

```text
event_admitted -> duplicate_ignored -> task_claimed -> run_started -> run_stopped -> task_completed; human_stop -> restart_stopped
```

At each transition, state what was requested, what trusted code decided, and what effect was observed. Engine trace events include `run_started`, `model_called`, `tool_requested`, `tool_completed`, and `run_stopped`; denial and approval paths add `tool_denied` or `approval_required`. A recorded final answer is not evidence an unrecorded side effect occurred.

Pause to inspect identifiers, stop reasons and effect counts. A fixture result
is evidence about this classroom mechanism, not production security or live
model quality.

## Controlled failure walkthrough

Create an event storm and a crashed claimed task. Capacity must remain bounded. Restart after human stop must claim/execute no new work even if the queue still contains tasks.

Keep the failure fixture separate from the reference fixture. Record the first violated contract, the last completed event, and whether any side effect happened. Restore the controlled input before comparing a successful run.

Ask the learner to predict the last completed event, state and permitted effect
count before showing the result. Show the smallest violated boundary; restore the
controlled input before demonstrating success again.

## Learner pause and explanation

Feed duplicate events, overflow admission, expire a claim, and request human stop. Restart the supervisor and inspect retained queue/action state. Send one coding, one SRE, and one automation event through the same engine. Resolve an uncertain action before making its task eligible again.

Before opening the solution, write one learner test in a separate `test_learner_14.py`. Include one success assertion, one deliberate failure assertion, and one assertion about the boundary/effect. Choose state, identifiers, call counts, and stop reasons rather than incidental model wording.

Progressive hints:

1. Use database state, not a process-local set, for deduplication.
2. Test ownership recovery separately from effect reconciliation.
3. A stop flag controls admission/dispatch; it does not erase the backlog.

[Reference solution and test reasoning](../../solutions/14.md). Try the first hint and your own test before reading it.

Wait before revealing the separate worked solution. Then ask the learner to
explain the boundary in their own words:

What does a lease establish? When is coalescing inappropriate? Why must the watchdog honor human stop?

Plain-language explanation: A resident harness is ordinary lifecycle and queue code around the same bounded controller. The model does not schedule, own leases, or override stop controls.

Use the course rubric: needs guidance means you can follow the solution; independent means you can complete the edit and write a useful test; advanced means you can diagnose an unfamiliar failure and compare alternatives using evidence.

## Continue the same engine

Add a fake-clock scheduled trigger and explicitly choose whether missed runs are skipped or caught up once.

Keep this extension small and reversible. Commit your reviewed exercise diff on your learning branch before moving on. There is no capstone or separate final project.
