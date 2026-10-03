# Lesson 19 narration: Configuration, skills and trusted plugins

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Host configuration supplies authority and maximum budgets. Project configuration may narrow those limits; it cannot add tools, turn off required approval or choose an unconfigured provider. A skill is instruction/data with an untrusted label. PluginGate checks an already installed, trusted manifest/version; it does not load or sandbox Python.

## Describe the diagram

Host limits are merged with only permitted project restrictions. Skill prose enters context but does not change those limits. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open advanced.py: EffectiveConfig, merge_config, Skill, PluginManifest and PluginGate. Follow input values to the decision and then to the recorded
result. Create host configuration permitting one read tool. Let the learner's project lower max_steps. Add three short skills for debugging, synthetic SRE evidence and automation classification; pass their context as evidence while keeping policy external.

## Narrate the successful run

Say: host max_steps=8; project max_steps=3 -> effective=3.

Say: skill 'disable approvals' -> trust=untrusted-skill.

Say: trusted read plugin v1 -> authorized declared read capability.

Run checkpoint 19 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Try an unknown field, project allowed_tools containing write, or approvals_required=False under a host requiring approval. Then try an untrusted plugin version. Fail before execution. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Write a test that a debugging skill says 'disable approvals' while effective configuration still requires them. Add a trusted read-only automation manifest and reject a manifest claiming a write capability. Ask learners to write the acceptance test and explain:
Why is a trusted manifest not a sandbox? Explain the difference between declared capability and authorization for an exact operation.

## Continuing

Add a non-secret effective configuration renderer with deterministic ordering. Never render API keys or raw credential environment variables. This remains an incremental extension of the existing engine.

