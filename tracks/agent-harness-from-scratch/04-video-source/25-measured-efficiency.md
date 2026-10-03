# Lesson 25 narration: Efficiency without weakening gates

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Measure first: redundant read count, context characters, steps, queue wait, usage and outcome. Cache only read observations with scope, logical key, state version and configuration version. JSON copies prevent caller mutation of the cached snapshot. A cache must never execute or verify a side effect.

## Describe the diagram

A matching scope/state/config key returns a copied observation; changed versions force a new read. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open advanced.py: ReadCache.read and compare_evaluations; core.py: context bounds. Follow input values to the decision and then to the recorded
result. Wrap repeated toy reads with ReadCache. Increment state_version when the toy file or synthetic observation changes. Compare a baseline loader count with the cached count, then rerun task outcome and permission checks.

## Narrate the successful run

Say: two reads with coding/file/v1/config1 -> loader called once.

Say: state changes to v2 -> loader called again.

Say: verification request -> bypass cache and observe actual state.

Run checkpoint 25 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Try operation='write' or verify_effect=True. Both raise BoundaryError before loader invocation. Reusing v1 after a file change would be a caller bug; version discipline is part of correctness, not automatic magic. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Add a test proving a changed state or config version reloads the observation. Mutate a returned dictionary and show the next cache result is unchanged. Report saved reads alongside unchanged task/safety outcomes. Ask learners to write the acceptance test and explain:
Which assumptions make a cache valid? Why is a faster unsafe run not an optimization?

## Continuing

Add selective memory retrieval or bounded batching, then compare across several fixture cases instead of one successful timing. This remains an incremental extension of the existing engine.

