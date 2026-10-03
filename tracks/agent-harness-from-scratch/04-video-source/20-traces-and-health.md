# Lesson 20 narration: Traces, usage and resident health

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Correlate run, task, action and provider call IDs before calculating totals. Record attempts separately from successful calls and mark missing token usage unknown. Resident health exposes stop, pause, draining, pending/uncertain tasks and stale workers. Health is evidence, not permission to restart.

## Describe the diagram

The report joins already recorded evidence by stable identifiers and marks missing measurements rather than inventing them. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open observability.py for TraceSink and UsageLedger. Follow correlation, redaction,
bounded capture and unknown-usage handling alongside the resident health API.

Open core.py: RunResult and Engine trace; persistence.py: event records; resident.py: ResidentQueue.health and heartbeat; advanced.py: Evaluation. Follow input values to the decision and then to the recorded
result. Build a small report from the existing events and health dictionary. Add queue-age and approval-wait calculations only when both timestamps are present. Return None when evidence is absent. Use an injected clock; do not time sleep calls.

## Narrate the successful run

Say: task admitted -> claimed -> action requested -> approved -> result -> completed.

Say: usage input known, output absent -> total unknown.

Say: health pending=0; uncertain=[]; human_stop=False.

Run checkpoint 20 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Seed a request with missing usage and a stale lease. A report must not show zero cost or silently restart the worker. A watchdog cannot clear human stop or bypass uncertain effects. Inspect which timestamp justifies each duration. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Write an unknown-usage test and a fake-clock stale-worker test. Add one report row for each scenario showing its stop reason and evidence source. Diagnose queue wait separately from provider time. Ask learners to write the acceptance test and explain:
Why does an empty usage dictionary mean unknown rather than free? Why is heartbeat liveness different from successful task progress?

## Continuing

Add configured price estimates with model/config version and uncertainty labels. Estimates are advisory; no paid experiment is needed. This remains an incremental extension of the existing engine.
