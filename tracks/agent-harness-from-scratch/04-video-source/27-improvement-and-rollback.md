# Lesson 27 narration: Controlled improvement and rollback

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Treat a proposal as a versioned prompt/config artifact, separate from policy and gate definitions. Host-owned correctness, policy, adversarial and held-out gates produce a recommendation. Exact human review binds the artifact digest and gate evidence. Passing tests do not authorize promotion. Promotion and rollback affect local artifacts only, not a deployment.

## Describe the diagram

A proposal passes independent gates, gets a recommendation, and becomes active only after review of its exact digest. The previous version remains available. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open advanced.py: PromotionStore.recommend, approve, promote, current and rollback. Follow input values to the decision and then to the recorded
result. On your learner branch propose a smaller bounded context setting for an existing scenario. Show the diff and collect real gate evidence. Store an accept/reject recommendation; exercise approval using a clearly labeled synthetic reviewer fixture, never a model-generated reviewer identity in a real host.

## Narrate the successful run

Label the checkpoint as a classroom mechanism demonstration: scripted offline
Engine outcome gates and a synthetic human-review fixture, with artifact-only
rollback. It does not measure live-model prompt quality or establish a beneficial
real improvement. A learner proposal needs independent fixture evidence.

Say: proposal passes all four gates -> accept, requires_review=True.

Say: promote before review -> rejected.

Say: fixture reviewer approves exact digest -> local version 2.

Say: rollback -> previous known-good artifact.

Run checkpoint 27 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

A faster proposal that disables approval fails the policy gate. Editing an approved artifact changes its digest and cannot reuse review. Missing or invented gates fail early. The proposer must not control the reviewer or gate results. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Compare one useful context reduction with one unsafe speed shortcut. Write a test that modifying one character after approval blocks promotion, then a test that rollback restores the original artifact. Ask learners to write the acceptance test and explain:
What does a passing gate prove, and what does review authorize? Why must the same proposer not set its own passing safety evidence?

## Continuing

Bind actual evaluation artifact hashes and immutable reviewer receipts; separately design authentication before considering real multi-user promotion. This remains an incremental extension of the existing engine.
