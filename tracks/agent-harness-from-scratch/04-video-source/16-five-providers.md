# Lesson 16 narration: Five provider adapters, one honest contract

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. Compare native envelopes before sharing parsing. OpenAI, DeepSeek and NVIDIA use chat-shaped requests here; Gemini uses content parts; Ollama uses native chat responses. Preserve native round-trip metadata where needed. Missing usage stays unknown. Configurable models are fixture names in offline examples, not promises of provider availability.

## Describe the diagram

The shared request passes through a provider-specific encoder and a fake transport; the decoder returns normalized text, tool calls, usage and metadata. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Open providers.py: _HTTPProvider, _ChatProvider, OpenAIProvider, GeminiProvider, DeepSeekProvider, OllamaProvider and NVIDIAProvider; tests/contract/test_providers.py; provider_fixtures/. Follow input values to the decision and then to the recorded
result. Add a provider-specific malformed-response case to the contract suite using FixtureTransport. Record the payload sent by the helper and assert its native fields rather than calling a live endpoint.

## Narrate the successful run

Say: fixture transport receives bounded request.

Say: native tool arguments normalize to a dictionary.

Say: Reply carries call ID and provider metadata.

Say: no network; no credentials; no tool execution.

Run checkpoint 16 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Configure NVIDIA without enabling a known model's tool capability, then pass tools. Expect unsupported_tools before transport. For Gemini, remove a required content envelope. For Ollama, replace object arguments with a malformed value. Diagnose the native boundary, not a controller failure. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Run the same read-only tool request through all five fixture adapters. Add one test for absent token usage and one malformed fixture test. Explain which native fields are preserved for follow-up turns. Ask learners to write the acceptance test and explain:
What does 'OpenAI-compatible' prove? Only a starting request shape; each model/endpoint still needs its own tool, error, usage and streaming checks.

## Continuing

Read the official docs linked in the provider guide. A bounded live smoke experiment requires a separately authorized opt-in, explicit model/endpoint and credentials; it is not required here. This remains an incremental extension of the existing engine.

