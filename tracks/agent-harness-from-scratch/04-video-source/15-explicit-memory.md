# Lesson 15 narration: Explicit memory and retention

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Keep durable task state in the action store. Put only deliberately selected cross-run facts into MemoryStore. Each record has scope, key, revision, value, source, creation time and expiry. Read the latest revision before checking expiry so an expired correction cannot resurrect an older fact. Retrieved rows remain untrusted evidence.

## Describe the diagram

A caller selects a fact, records its origin and expiry, then retrieves the latest scoped revision as evidence for later context. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open advanced.py: MemoryStore.put, inspect, retrieve, delete and prune. Follow input values to the decision and then to the recorded
result. In your learner branch, add a small remember_fact helper that chooses a scope and requires an explicit public classification. Return the stored revision, not an assertion that the fact is true. Keep host policy separate.

## Narrate the successful run

Say: put(scope='coding', key='style') -> revision=1.

Say: correct same key -> revision=2.

Say: retrieve coding -> latest revision, trust=untrusted-memory.

Say: delete -> no later retrieval.

Run checkpoint 15 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Save a long-lived revision and then a short-lived correction. Move an injected clock past the correction's expiry. Retrieval must return no fact, rather than the old revision. Inspection should still explain both revisions until prune/delete. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Save 'use spaces' for the toy coding project, 'health fixture is synthetic' for the toy service, and 'ask before artifact replacement' for automation. Correct the coding fact, delete the automation preference, and write a test that another scope cannot retrieve the coding convention. Ask learners to write the acceptance test and explain:
Why is a memory record not a permission grant? Explain why the newest record may be unavailable even when an older record has a later expiry.

## Continuing

Add a text search index only after comparing it to the small case-insensitive query; preserve scope and expiry checks. This remains an incremental extension of the existing engine.

