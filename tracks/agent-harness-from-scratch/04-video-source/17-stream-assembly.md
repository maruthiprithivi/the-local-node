# Lesson 17 narration: Streaming without partial tool execution

Transcript and recording script; no recording is claimed. Read the lab alongside
this text. Caption future recordings with these words and describe visual changes
aloud; do not rely on color or audio alone.

## Opening

Today we extend the same small Python harness. A stream is a series of fragments, not a series of authorized actions. Assemble ordered normalized text/tool/end events; bound bytes, bind fragments to a stable call ID/name, parse complete JSON, then validate every call. Disconnect, cancellation and malformed siblings discard pending calls. This lesson implements fixture stream assembly; the delivered HTTP adapters remain synchronous. Native SSE/NDJSON decoders and transport cancellation are separate unfinished integration work.

## Describe the diagram

Fragments accumulate in a bounded buffer. Only an explicit end followed by complete JSON and contract validation can expose a tool call. Read every arrow in order. The host-owned boundary is ordinary program
logic, visible outside the model's suggestions.

## Walk through source

Also open streaming.py. read_stream consumes supplied native SSE or NDJSON
fixtures, checks provider termination and normalizes events for the assembler.
It does not open a live stream. Clearly distinguish native decoder fixtures from
unsupported live HTTP streaming/cancellation.

Open advanced.py: StreamAssembler.feed and finish; providers.py synchronous boundary. Follow input values to the decision and then to the recorded
result. Add a named toy-tool validator to StreamAssembler, then feed a JSON argument across two fragments. Keep the executor outside the assembler. The minimal change is a validator and test fixture, not streaming network code.

## Narrate the successful run

Say: sequence 0: tool id=read-1 delta={"path":.

Say: sequence 1: same tool delta="toy.py"}.

Say: sequence 2: end.

Say: finish -> one validated call; repeated finish returns same result.

Run checkpoint 17 for coding, SRE and automation. Pause to inspect each result.
The lab's trace describes meaning, not exact terminal formatting.

## Investigate a failure

Omit end or feed sequence 2 before sequence 1. finish must label interruption and return zero calls. If one sibling is malformed, no sibling executes. Cancellation after a partial request also returns zero calls. Ask learners to predict the effect count and recovery state before
showing the result. Leave time to try the progressive hints before revealing the
separate solution.

## Learner pause

Write tests for split arguments, changed tool names, out-of-order fragments, disconnect and cancelled finish. Count validator invocations and prove repeated finish does not validate twice. Ask learners to write the acceptance test and explain:
Why can displaying partial text be acceptable while executing a partial tool request is not? Display itself still needs redaction and bounded capture.

## Continuing

Implement one provider-specific decoder from its documented stream format, preserving terminal rules, then add fixtures before enabling transport. This remains an incremental extension of the existing engine.
