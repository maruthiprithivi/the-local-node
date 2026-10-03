# Lesson 24 narration: Two workers and one global budget

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Start with two trusted cooperative read-only workers. Each has a stable ID and explicit scope. Admission caps tasks and concurrency; one locked shared budget pays for worker admission and observations. Results are structured untrusted evidence. Recursive coordination and mutations are denied. Threads share memory; they are not isolation.

## Describe the diagram

A coordinator admits at most two concurrent workers, who consume one shared budget and return scoped observations. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open advanced.py: WorkerTask, WorkerContext.read, SharedBudget and coordinate. Follow input values to the decision and then to the recorded
result. Create two inspection tasks for independent toy files, two synthetic evidence sources, or two automation classifications. Each worker must call context.read using its assigned scope. Return evidence to the coordinator; do not apply a worker-proposed mutation.

## Narrate the successful run

Say: admit worker A + worker B -> 2 budget units.

Say: one read each -> 2 more units.

Say: results stable input order; trust=untrusted-worker.

Say: coordinator decides later actions through ordinary policy.

Run checkpoint 24 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Show conflicting dictionaries from the two workers. merge_worker_findings keeps
the conflicting key out of accepted findings and records both values for review.
Worker confidence cannot settle a conflict or grant mutation authority.

Ask a worker to read another scope or recursively call coordinate. Its result is failed, not silently dropped. Set cancellation before admission and verify no observation callback runs. Allocation between concurrent workers may vary; test total limits, not a scheduling race. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Write a worker that attempts the wrong scope, then prove failures remain visible. Compare two workers with sequential reads: record useful units and overhead rather than assuming parallel is always faster. Ask learners to write the acceptance test and explain:
When is sequential work simpler? Why can't Python threads forcibly stop a hung tool or enforce a malicious callable's scope?

## Continuing

Add process isolation with explicit IPC and cleanup in an approved environment, retaining the same policy and budget contracts. This remains an incremental extension of the existing engine.
