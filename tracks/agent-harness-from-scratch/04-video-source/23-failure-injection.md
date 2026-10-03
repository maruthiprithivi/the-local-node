# Lesson 23 narration: Stress, injection and failure testing

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. A failure matrix names injection point, expected state, permitted effects and recovery. Cover malformed replies, rate limits, huge output, queue storms, storage failure, stale approval, expired lease, hung callback, injected instructions, traversal/symlink attempts and crashes after effects. Use synthetic fixtures; do not probe real infrastructure.

## Describe the diagram

A synthetic fault reaches a named boundary; a deterministic check proves a limit or explicit uncertain state, then recovery uses evidence. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open core.py budgets/retry/context; tools.py validation/path gates; resident.py enqueue/recover; persistence.py uncertain states; advanced.py StreamAssembler. Follow input values to the decision and then to the recorded
result. Choose one boundary, add a failing fixture and a precise expected state. Fix the smallest bug without broadening policy. For a queue storm, assert accepted task count never exceeds capacity and rejected events remain visible to the caller.

## Narrate the successful run

Say: burst exceeds queue capacity -> explicit QueueFull.

Say: expired running lease -> uncertain, not queued.

Say: untrusted log says disable policy -> policy remains unchanged.

Say: human stop persists across reopen.

Run checkpoint 23 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Use a callback that mutates a toy artifact and raises before recording completion. Treat its result as uncertain; inspect the artifact before resolution. A thread-based cooperative runner cannot forcibly kill a malicious/hung callback; list that unsupported threat. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Add one adversarial case that first reveals a real regression in your learner branch, then fix it. Include a test for cancelled partial streams returning no calls and a paragraph identifying what the test does not prove. Ask learners to write the acceptance test and explain:
What is the difference between testing a path restriction and proving isolation? Why is unavailable storage a reason to stop before an unrecorded effect?

## Continuing

Create a matrix table for every critical transition and add process-isolated hung-tool experiments only in a separately authorized disposable environment. This remains an incremental extension of the existing engine.

