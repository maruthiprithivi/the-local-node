# Lesson 18 narration: Model switching and constrained handover

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. A handover packet records goal, evidence, changes, completed and pending action IDs, uncertainty, permissions, required capabilities and remaining steps. The host chooses destinations and data localities. Validation creates an auditable switch record; it does not contact a provider or resume actions by itself.

## Describe the diagram

The first run packages evidence and remaining constraints. Host validation checks the receiver before continuation. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open advanced.py: Handover and validate_handover; persistence.py completed/uncertain actions. Follow input values to the decision and then to the recorded
result. Construct a packet after the toy coding read or SRE observation. Validate a switch between two fake-local destinations, then give the receiver only recorded results and pending work. Reuse the durable action store rather than re-running completed effects.

## Narrate the successful run

Say: goal + completed={read-1} + pending={diagnose-2}.

Say: destination fake-b configured; local; read-only; steps <= remaining.

Say: switch record -> trust=untrusted-handover.

Say: receiver continues pending work only.

Run checkpoint 18 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Attempt local-to-hosted fallback without approved hosted locality, add receiver permissions, or increase remaining steps. Each change must raise BoundaryError. A provider outage cannot silently become consent to export content. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Build three packets for coding, SRE and automation. For each, preserve one completed ID and one uncertainty. Write a test proving that a completed action cannot also appear as pending. Ask learners to write the acceptance test and explain:
Which facts are evidence and which values are host constraints? Why must a model-provided handover be revalidated?

## Continuing

Connect a validated packet to Engine using durable results, then test an interrupted run without repeating its mutation. This remains an incremental extension of the existing engine.

