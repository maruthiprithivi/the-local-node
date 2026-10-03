# One boundary, five provider helpers

The engine imports `Provider`, `Reply`, and `ToolCall` from
`course_harness.providers`. Each provider implements
`complete(messages, tools=()) -> Reply`. It returns text, proposed calls, usage,
and opaque metadata. It never executes a tool. The controller checks each proposal
against its registry, schema, mode, budgets, and approvals.

Messages use `role` and text `content`. Tools use `name`, `description`, and an
object `parameters` schema. Use `assistant_message(reply)` to append an assistant
turn. Append results with `role="tool"`, `tool_call_id=call.id`, `name=call.name`,
`content=<serialized result>`, and `metadata=call.metadata`. Keeping metadata is
essential: native Gemini parts can contain opaque thought signatures, and native
Ollama calls contain argument objects. Do not print native metadata in ordinary
traces or copy it to another provider. Native history is provider-specific.

```python
from course_harness.providers import FakeProvider, Reply, ToolCall

provider = FakeProvider([
    Reply(calls=(ToolCall("status-1", "read_status", {"service": "demo"}),)),
    Reply("The synthetic service is healthy."),
])
```

All course scenarios use scripted fake replies by default. Fake exhaustion fails
explicitly rather than quietly inventing a final answer. `FixtureTransport`
captures requests without storing authentication headers, returns synthetic wire
responses, and can raise a scripted `ProviderError`. The JSON files in
`provider_fixtures/` are synthetic contract fixtures, not recordings of real model
behavior. Contract tests cover all five helpers, malformed arguments, request and
response bounds, metadata round trips, explicit network opt-in, and error handling.

## Optional live boundary

Constructing a helper never contacts a service. Calling it without an injected
transport raises `live_disabled`, unless the caller sets `allow_live=True`.
Hosted helpers also require an explicitly passed `api_key`. Keys are never read
from the environment automatically. Ollama uses a loopback endpoint,
and still requires opt-in because running a local model consumes resources.
These exercises do not authorize live calls or paid usage. On this project the
Mac is source-only; run validation only through the approved GCP workflow.

Each helper accepts an explicit `endpoint` override on its reviewed origin;
Ollama also allows `localhost` or `::1` and an explicit loopback port. Foreign
origins, URL credentials, query strings, and fragments are rejected. Extending
this allowlist for a gateway is a separate reviewable exercise. The output cap
defaults to 512 tokens, with a maximum configurable value of 4096: OpenAI sends
`max_completion_tokens`, DeepSeek/NVIDIA `max_tokens`, Gemini
`generationConfig.maxOutputTokens`, and Ollama `options.num_predict`. A provider
may count thinking tokens differently; local size and turn limits still apply.

Choose a model yourself using its current official documentation. No model name
or compatibility is silently assumed. NVIDIA rejects tools by default; only set
`supports_tools=True` after verifying the selected model's documented capability.
For any provider, set `supports_tools=False` for a text-only model. Capability flags
are caller configuration, not automatic discovery or proof of server behavior.

Live helpers support synchronous text and tool proposals. Each exposes immutable
`capabilities`: synchronous/text are true; tools reflect the configured model;
streaming/structured_output are false; context_window is unknown (`None`). Call
`provider.require("streaming")` or another feature before attempting it: unknown or
unsupported features fail explicitly. No live HTTP streaming fallback exists.
Images, audio, provider built-in tools, automatic retries, and remote tool
execution remain unsupported.

## Offline native streaming (lesson 17)

`course_harness.streaming.read_stream(provider_name, chunks, validate)` consumes
supplied byte fixtures and feeds normalized ordered events into `StreamAssembler`.
It implements Chat Completions SSE deltas plus `[DONE]` for OpenAI, DeepSeek and
NVIDIA; Gemini SSE candidate parts with `finishReason`; and Ollama NDJSON with
`done:true`. Chat calls accumulate by native index, preserving fragmented identity
and JSON arguments. Gemini/Ollama's supported function calls use complete native
argument objects. Gemini experimental partial arguments are rejected explicitly.
Only one candidate/choice and text/function tools are supported.

```python
from pathlib import Path
from course_harness.streaming import read_stream

validated = []  # A pure schema/allowlist checker belongs here; do not execute tools.
decoded = read_stream("openai", [Path("provider_fixtures/chat-stream.sse").read_bytes()],
                      validated.append)
assert not decoded.response.interrupted
assert decoded.response.calls[0]["arguments"] == {"service": "demo"}
```

The offline reader buffers bounded bytes, handles arbitrary UTF-8/chunk boundaries,
and publishes calls only after native termination, clean input exhaustion, full
JSON parsing, and contract validation. Missing terminators, malformed frames,
truncation, cancellation, and disconnect discard every proposal. The returned
events teach assembly; they are not authorization to execute tools. A controller
must still apply its policy and approval gates. Cancellation is cooperative at
chunk/frame boundaries and cannot interrupt a blocking byte iterator.

Limits: 1 MiB input, 4096 supplied chunks, 1024 data frames, bounded normalized
events, sixteen calls, 16 KiB arguments, and 8 KiB assembled output by default.
Optional usage stays unknown when absent. Native Gemini parts retain signatures
as opaque metadata. This closes the offline decoder checkpoint; live HTTP stream
acquisition, reconnection, deadline enforcement, and model-specific streaming
compatibility are separate unsupported transport features.

Streaming shapes were checked against [OpenAI streaming events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events),
[OpenAI tool delta examples](https://developers.openai.com/api/docs/guides/function-calling#streaming),
[Gemini streamGenerateContent](https://ai.google.dev/api/generate-content#method:-models.streamgeneratecontent),
[Ollama streaming](https://docs.ollama.com/api/streaming), and the
[NVIDIA model stream reference](https://docs.api.nvidia.com/nim/reference/deepseek-ai-deepseek-v4-flash-infer).
DeepSeek's [first-call guide](https://api-docs.deepseek.com/guides/reasoning_model/)
confirms its OpenAI API format and stream opt-in. Its detailed stream reference
remained inaccessible during this review; the decoder has synthetic protocol
contract tests, still unrun, and must be rechecked against the detailed official
reference before live use.

## Wire formats checked against official docs

Documentation reviewed on 2026-10-03; model availability and features can change.
The DeepSeek tool guide was accessible; its linked full API and thinking-mode
references timed out during this review. Recheck those references before any live
DeepSeek use, especially generation limits and thinking-model history requirements.

| Helper | Explicit endpoint and supported subset | Official reference |
| --- | --- | --- |
| OpenAI | `POST https://api.openai.com/v1/chat/completions`; `messages`, function tools, `stream:false`; parse `choices[0].message` and JSON-string arguments | [Chat Completions create reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) |
| Gemini | `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`; `contents`, `systemInstruction`, `functionDeclarations`; parse native parts and argument objects | [generateContent reference](https://ai.google.dev/api/generate-content), [function calling](https://ai.google.dev/gemini-api/docs/function-calling), [thought signatures](https://ai.google.dev/gemini-api/docs/thought-signatures) |
| DeepSeek | `POST https://api.deepseek.com/chat/completions`; documented Chat Completions tool/result shape; preserve returned `reasoning_content` on later turns | [Tool calls](https://api-docs.deepseek.com/guides/tool_calls/), [thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/) |
| Ollama | `POST http://127.0.0.1:11434/api/chat`; force `stream:false` because streaming defaults on; argument objects and tool result `tool_name` | [Chat endpoint](https://docs.ollama.com/api/chat), [tool calling](https://docs.ollama.com/capabilities/tool-calling), [generation parameters](https://docs.ollama.com/modelfile) |
| NVIDIA | `POST https://integrate.api.nvidia.com/v1/chat/completions`; text Chat Completions subset; model-specific tool support must be verified before opt-in | [Hosted LLM API catalog](https://docs.api.nvidia.com/nim/reference/llm-apis), [a hosted model reference with max_tokens](https://docs.api.nvidia.com/nim/reference/deepseek-ai-deepseek-v4-flash-infer) |

Sharing an endpoint shape does not establish equal semantics. DeepSeek strict
schema mode is documented as a separate beta configuration, which this helper
does not enable. Gemini schema support varies; use simple object schemas for the
course. The NVIDIA catalog confirms its hosted endpoint but does not promise tool
support across models. Thought signatures remain opaque; preserve their complete
parts and ordering. The normalized call ID is only a harness correlation ID when
a provider does not supply one.

Synthetic Gemini/Ollama call IDs include the adapter's response counter, so calls
in different turns do not accidentally collide. Persisted controller histories
should namespace these IDs by run as well; restarting a provider resets its counter.

## Failure and usage contract

`ProviderError` contains a redacted category, optional status, and retry hint.
HTTP 401/403 map to `authentication`, 429 to `rate_limit`, and 5xx to `server`.
Timeout and connection failures are retryable hints; no helper retries. Malformed
responses, invalid argument JSON, refusal, truncated generations, duplicate call
IDs, unsupported tools, and fixture exhaustion stop the turn. Controllers must
bound retries, use backoff, and avoid repeating side effects. Remote error bodies
and credential-bearing exception messages are not included in errors.

JSON request and response sizes are bounded at 1 MiB, tool arguments at 16 KiB,
and proposed calls at sixteen. The HTTP timeout is bounded at sixty seconds and
redirects are rejected to avoid forwarding credentials. These are course limits,
not a production security guarantee or a complete denial-of-service defense.

`usage` exposes known `input_tokens` and `output_tokens`. Missing counts remain
unknown. Gemini candidate output counts may exclude thinking tokens; these fields
alone must not be used as a billing estimate or authoritative total budget.
Fixture tokens are made-up numbers for deterministic exercises. Enforce turn,
wall-time, response-size, and call limits independently of reported usage.

Validation status: source reviewed; contract tests have **not been executed** on
the Mac. No live model calls were made. Remote test execution is pending an approved
validation route; an offline fixture pass will not prove live API compatibility.
