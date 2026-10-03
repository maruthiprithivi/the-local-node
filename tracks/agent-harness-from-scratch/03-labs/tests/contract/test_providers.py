"""Offline contracts. Run only on the approved remote validation worker."""
import json
from pathlib import Path

import pytest

from course_harness.providers import (
    DeepSeekProvider, FakeProvider, FixtureTransport, GeminiProvider,
    MAX_ARGUMENT_BYTES, MAX_BYTES, MAX_CALLS, NVIDIAProvider, OllamaProvider,
    OpenAIProvider, ProviderError, Reply, ToolCall, assistant_message,
)

FIXTURES = Path(__file__).resolve().parents[2] / "provider_fixtures"
MESSAGES = [{"role": "user", "content": "Read demo service status."}]
TOOLS = [{"name": "read_status", "description": "Read synthetic status", "parameters": {
    "type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}}]


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.mark.parametrize("provider,shape", [
    (OpenAIProvider, "chat"), (DeepSeekProvider, "chat"),
    (NVIDIAProvider, "chat"), (GeminiProvider, "gemini"), (OllamaProvider, "ollama"),
])
def test_five_helpers_normalize_native_tool_calls(provider, shape):
    transport = FixtureTransport([fixture(shape)])
    reply = provider("fixture-model", transport=transport, supports_tools=True).complete(MESSAGES, TOOLS)
    assert reply.calls[0].name == "read_status"
    assert reply.calls[0].arguments == {"service": "demo"}
    assert reply.usage == {"input_tokens": 12, "output_tokens": 7}
    payload = transport.requests[0]["payload"]
    if shape == "gemini":
        assert payload["contents"][0]["role"] == "user"
        assert payload["tools"][0]["functionDeclarations"] == TOOLS
    else:
        assert payload["stream"] is False
        assert payload["tools"][0]["function"] == TOOLS[0]


def test_gemini_round_trip_keeps_signature_and_function_response_id():
    transport = FixtureTransport([fixture("gemini"), fixture("gemini")])
    provider = GeminiProvider("fixture-model", transport=transport)
    reply = provider.complete(MESSAGES, TOOLS)
    call = reply.calls[0]
    provider.complete(MESSAGES + [assistant_message(reply), {
        "role": "tool", "name": call.name, "tool_call_id": call.id,
        "content": '{"status":"healthy"}', "metadata": call.metadata,
    }], TOOLS)
    content = transport.requests[1]["payload"]["contents"]
    assert content[1] == fixture("gemini")["candidates"][0]["content"]
    assert content[2]["parts"][0]["functionResponse"]["id"] == "native-1"


def test_ollama_round_trip_uses_object_arguments_and_tool_name():
    transport = FixtureTransport([fixture("ollama"), fixture("ollama")])
    provider = OllamaProvider("fixture-model", transport=transport)
    reply = provider.complete(MESSAGES, TOOLS)
    provider.complete(MESSAGES + [assistant_message(reply), {
        "role": "tool", "name": "read_status", "content": "healthy",
    }], TOOLS)
    messages = transport.requests[1]["payload"]["messages"]
    assert isinstance(messages[1]["tool_calls"][0]["function"]["arguments"], dict)
    assert messages[2]["tool_name"] == "read_status"
    assert "tool_call_id" not in messages[2]


@pytest.mark.parametrize("provider", [OpenAIProvider, DeepSeekProvider, NVIDIAProvider,
                                      GeminiProvider, OllamaProvider])
def test_live_calls_disabled_before_transport_or_credentials(provider):
    with pytest.raises(ProviderError, match="live_disabled"):
        provider("fixture-model").complete(MESSAGES)


def test_nvidia_requires_model_tool_capability_opt_in():
    transport = FixtureTransport([fixture("chat")])
    with pytest.raises(ProviderError, match="unsupported_tools"):
        NVIDIAProvider("unverified-model", transport=transport).complete(MESSAGES, TOOLS)
    assert transport.requests == []


def test_malformed_arguments_never_reach_engine():
    with pytest.raises(ProviderError, match="malformed_arguments"):
        OpenAIProvider("fixture-model", transport=FixtureTransport([fixture("malformed")])).complete(MESSAGES)


@pytest.mark.parametrize("raw,category", [
    ({"choices": []}, "malformed_response"),
    ({"error": {"message": "SECRET"}}, "remote_error"),
    ({"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]}, "truncated"),
    ({"choices": [{"message": {"content": "", "refusal": "SECRET"}}]}, "refusal"),
])
def test_error_categories_are_redacted(raw, category):
    with pytest.raises(ProviderError) as failure:
        OpenAIProvider("fixture-model", transport=FixtureTransport([raw])).complete(MESSAGES)
    assert failure.value.category == category
    assert "SECRET" not in str(failure.value)


def test_absent_usage_is_unknown():
    raw = {"choices": [{"message": {"content": "hello"}}]}
    reply = OpenAIProvider("fixture-model", transport=FixtureTransport([raw])).complete(MESSAGES)
    assert reply.usage == {}


@pytest.mark.parametrize("mutation", ["arguments", "calls", "response"])
def test_data_bounds(mutation):
    raw = fixture("chat")
    if mutation == "arguments":
        raw["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = json.dumps({"x": "x" * MAX_ARGUMENT_BYTES})
    elif mutation == "calls":
        raw["choices"][0]["message"]["tool_calls"] *= MAX_CALLS + 1
    else:
        raw["padding"] = "x" * MAX_BYTES
    with pytest.raises(ProviderError, match="size_limit"):
        OpenAIProvider("fixture-model", transport=FixtureTransport([raw])).complete(MESSAGES)


def test_request_bound_prevents_transport():
    transport = FixtureTransport([fixture("chat")])
    with pytest.raises(ProviderError, match="size_limit"):
        OpenAIProvider("fixture-model", transport=transport).complete([
            {"role": "user", "content": "x" * MAX_BYTES}])
    assert transport.requests == []


def test_fake_is_scripted_isolated_and_explicitly_exhausted():
    call = ToolCall("demo-1", "read_status", {"service": "demo"})
    provider = FakeProvider([Reply(calls=(call,)), Reply("healthy")])
    first = provider.complete(MESSAGES, TOOLS)
    first.calls[0].arguments["service"] = "changed"
    assert call.arguments == {"service": "demo"}
    assert provider.complete(MESSAGES).text == "healthy"
    with pytest.raises(ProviderError, match="fixture_exhausted"):
        provider.complete(MESSAGES)


def test_transport_failure_has_retry_hint_without_retry():
    transport = FixtureTransport([ProviderError("rate_limit", retryable=True, status=429)])
    with pytest.raises(ProviderError) as failure:
        OpenAIProvider("fixture-model", transport=transport).complete(MESSAGES)
    assert failure.value.retryable
    assert failure.value.status == 429
    assert len(transport.requests) == 1


@pytest.mark.parametrize("provider,shape", [(GeminiProvider, "gemini"), (OllamaProvider, "ollama")])
def test_synthetic_call_ids_are_unique_between_turns(provider, shape):
    raw = fixture(shape)
    if shape == "gemini":
        del raw["candidates"][0]["content"]["parts"][0]["functionCall"]["id"]
    instance = provider("fixture-model", transport=FixtureTransport([raw, raw]))
    assert instance.complete(MESSAGES).calls[0].id != instance.complete(MESSAGES).calls[0].id


@pytest.mark.parametrize("provider,shape,field", [
    (OpenAIProvider, "chat", "max_completion_tokens"),
    (DeepSeekProvider, "chat", "max_tokens"),
    (NVIDIAProvider, "chat", "max_tokens"),
    (GeminiProvider, "gemini", "maxOutputTokens"),
    (OllamaProvider, "ollama", "num_predict"),
])
def test_provider_specific_generation_cap(provider, shape, field):
    transport = FixtureTransport([fixture(shape)])
    provider("fixture-model", transport=transport, max_output_tokens=123).complete(MESSAGES)
    payload = transport.requests[0]["payload"]
    nested = payload.get("generationConfig", payload.get("options", payload))
    assert nested[field] == 123


def test_endpoint_override_stays_on_reviewed_origin():
    transport = FixtureTransport([fixture("chat")])
    instance = OpenAIProvider("fixture-model", api_key="SECRET", transport=transport,
                              endpoint="https://example.invalid/v1/chat/completions")
    with pytest.raises(ProviderError, match="untrusted_endpoint"):
        instance.complete(MESSAGES)
    assert transport.requests == []


def test_ollama_endpoint_can_select_explicit_loopback_port():
    transport = FixtureTransport([fixture("ollama")])
    OllamaProvider("fixture-model", transport=transport,
                   endpoint="http://localhost:11435/api/chat").complete(MESSAGES)
    assert transport.requests[0]["url"] == "http://localhost:11435/api/chat"


def test_fake_malformed_fixture_stops_before_return():
    with pytest.raises(ProviderError, match="malformed_fixture"):
        FakeProvider([{"text": "not a Reply"}]).complete(MESSAGES)


def test_live_opt_in_cannot_be_a_truthy_string():
    with pytest.raises(ProviderError, match="configuration"):
        OpenAIProvider("fixture-model", allow_live="false")


def test_deepseek_preserves_native_reasoning_history():
    raw = fixture("chat")
    raw["choices"][0]["message"]["reasoning_content"] = "synthetic-native-content"
    transport = FixtureTransport([raw, raw])
    provider = DeepSeekProvider("fixture-model", transport=transport)
    reply = provider.complete(MESSAGES)
    provider.complete(MESSAGES + [assistant_message(reply)])
    assert transport.requests[1]["payload"]["messages"][1]["reasoning_content"] == "synthetic-native-content"
