# Lesson 26 narration: Resident operations and graceful degradation

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Separate persisted UTC schedule slots from monotonic execution deadlines. Schedule supports elapsed intervals with timezone presentation, not civil-time cron. missed='latest' admits at most one catch-up; missed='skip' discards gaps. overlap='skip' avoids concurrent logical jobs; overlap='queue' still obeys capacity. Provider outages remain on the configured destination.

## Describe the diagram

Scheduling computes a UTC slot and applies documented catch-up and overlap decisions before admission. Operator controls persist in the store. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open resident.py: Schedule.admit, ResidentQueue.pause/drain/stop/resume/health/recover; persistence.py control state. Follow input values to the decision and then to the recorded
result. Add an operator helper that first prints health/inspect, then offers pause, drain, stop or explicit human-stop reset. Keep reconciliation separate. Simulate a schedule gap with an aware datetime; do not wait for a real outage.

## Narrate the successful run

Say: downtime across 5 slots; latest -> one newest task.

Say: pause -> no claim/admission.

Say: drain -> no new admission, accepted work can finish.

Say: stop -> persistent human_stop; resume without reset rejected.

Run checkpoint 26 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Expire a worker lease, call recover and reopen the store. The task stays uncertain. resume cannot declare its effect absent or clear stop implicitly. Cooperative callbacks need explicit stop checks; there is no real process watchdog that can kill them. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Test latest versus skip catch-up, overlap rejection and stop across restart. Write a four-step runbook: inspect, stop, observe/reconcile uncertain effects, explicitly resume. Include a provider outage escalation, never an implicit hosted fallback. Ask learners to write the acceptance test and explain:
Why use monotonic time for a deadline but persisted wall time for a future schedule? Which behavior is deliberately unsupported by this interval scheduler?

## Continuing

Add civil-time schedules with explicit DST ambiguity/nonexistence rules and timezone database fixtures before promising '9am daily'. This remains an incremental extension of the existing engine.

