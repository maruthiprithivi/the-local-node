"""Provider-native streaming contracts; offline fixtures, remote execution only."""
from pathlib import Path
import pytest

from course_harness.providers import (
    MAX_BYTES, DeepSeekProvider, FakeProvider, GeminiProvider, NVIDIAProvider,
    OllamaProvider, OpenAIProvider, ProviderError,
)
from course_harness.streaming import read_stream

FIXTURES = Path(__file__).resolve().parents[2] / "provider_fixtures"


def fixture(provider):
    name = "chat-stream.sse" if provider in {"openai", "deepseek", "nvidia"} else (
        "gemini-stream.sse" if provider == "gemini" else "ollama-stream.ndjson")
    return (FIXTURES / name).read_bytes()


@pytest.mark.parametrize("provider", ["openai", "deepseek", "nvidia", "gemini", "ollama"])
def test_native_streams_publish_validated_calls_only_after_completion(provider):
    validated = []
    result = read_stream(provider, [fixture(provider)], validated.append)
    assert not result.response.interrupted
    assert result.response.text == "Inspecting "
    assert result.response.calls[0]["arguments"] == {"service": "demo"}
    assert validated == list(result.response.calls)
    assert result.events[-1]["kind"] == "end"
    assert [event["sequence"] for event in result.events] == list(range(len(result.events)))
    assert result.usage == {"input_tokens": 12, "output_tokens": 7}


@pytest.mark.parametrize("provider", ["openai", "gemini", "ollama"])
def test_native_chunk_boundaries_do_not_change_result(provider):
    raw = fixture(provider).replace(b"Inspecting ", "Inspecting café ".encode())
    result = read_stream(provider, [raw[index:index+1] for index in range(len(raw))], lambda call: None)
    assert not result.response.interrupted
    assert result.response.text == "Inspecting café "


@pytest.mark.parametrize("provider", ["openai", "deepseek", "nvidia", "gemini", "ollama"])
def test_missing_native_termination_discards_pending_calls(provider):
    raw = fixture(provider)
    if provider in {"openai", "deepseek", "nvidia"}:
        raw = raw.replace(b"data: [DONE]", b": removed terminal")
    elif provider == "gemini":
        raw = raw.replace(b',"finishReason":"STOP"', b"")
    else:
        raw = raw.replace(b'"done":true', b'"done":false')
    validated = []
    result = read_stream(provider, [raw], validated.append)
    assert result.response.interrupted and result.response.calls == ()
    assert result.response.reason == "interrupted_stream"
    assert validated == [] and result.events == ()


@pytest.mark.parametrize("provider", ["openai", "gemini", "ollama"])
def test_native_truncation_discards_proposals(provider):
    raw = fixture(provider)
    if provider == "openai":
        raw = raw.replace(b'"finish_reason":"tool_calls"', b'"finish_reason":"length"')
    elif provider == "gemini":
        raw = raw.replace(b'"finishReason":"STOP"', b'"finishReason":"MAX_TOKENS"')
    else:
        raw = raw.replace(b'"done_reason":"stop"', b'"done_reason":"length"')
    result = read_stream(provider, [raw], lambda call: None)
    assert result.response.reason == "truncated" and result.response.calls == ()


@pytest.mark.parametrize("provider", ["openai", "gemini", "ollama"])
def test_cancellation_discards_all_proposals_without_validation(provider):
    validated = []
    result = read_stream(provider, [fixture(provider)], validated.append, cancelled=lambda: True)
    assert result.response.reason == "cancelled" and result.response.calls == ()
    assert validated == []


def test_chat_native_fragmented_identity_and_arguments_are_assembled():
    raw = fixture("openai").replace(b'"id":"call-1"', b'"id":"call"')
    raw = raw.replace(b'"name":"read_status"', b'"name":"read_"')
    raw = raw.replace(b'"index":0,"function":{"arguments"',
                      b'"index":0,"id":"-1","function":{"name":"status","arguments"')
    result = read_stream("openai", [raw], lambda call: None)
    assert result.response.calls == ({"id": "call-1", "name": "read_status", "arguments": {"service": "demo"}},)


def test_usage_is_optional_and_not_guessed():
    raw = fixture("openai")
    raw = b"\n\n".join(frame for frame in raw.split(b"\n\n") if b'"usage"' not in frame)
    result = read_stream("openai", [raw], lambda call: None)
    assert not result.response.interrupted and result.usage == {}


def test_gemini_preserves_opaque_native_parts():
    result = read_stream("gemini", [fixture("gemini")], lambda call: None)
    assert result.metadata["gemini_parts"][1]["thoughtSignature"] == "synthetic-opaque-signature"


def test_unfinished_sse_frame_and_invalid_utf8_fail_closed():
    for raw in (fixture("openai").rstrip(), b"\xff"):
        result = read_stream("openai", [raw], lambda call: None)
        assert result.response.interrupted and result.response.calls == ()


def test_bytes_frames_chunks_and_output_are_bounded():
    for raw in ([b"x" * (MAX_BYTES + 1)], [b": comment\n\n" * 1025], [b""] * 4097):
        result = read_stream("openai", raw, lambda call: None)
        assert result.response.interrupted and result.response.calls == ()
    result = read_stream("openai", [fixture("openai")], lambda call: None, output_limit=1)
    assert result.response.interrupted and result.response.calls == ()


def test_extra_data_after_terminal_cannot_publish_calls():
    raw = fixture("openai") + b'data: {"choices":[]}\n\n'
    assert read_stream("openai", [raw], lambda call: None).response.calls == ()


def test_interrupted_byte_iterator_cannot_publish_calls():
    def interrupted():
        yield fixture("openai")
        raise OSError("synthetic disconnect")
    result = read_stream("openai", interrupted(), lambda call: None)
    assert result.response.interrupted and result.response.calls == ()


def test_done_without_finish_reason_is_not_a_complete_chat_stream():
    validated = []
    raw = fixture("openai").replace(b'"finish_reason":"tool_calls"', b'"finish_reason":null')
    result = read_stream("openai", [raw], validated.append)
    assert result.response.reason == "invalid_termination"
    assert result.response.calls == () and validated == []


def test_malformed_native_argument_json_never_reaches_validator():
    raw = fixture("openai").replace(b'{\\"service\\":', b'not-json')
    validated = []
    result = read_stream("openai", [raw], validated.append)
    assert result.response.interrupted and result.response.calls == ()
    assert validated == []


def test_gemini_experimental_partial_argument_shape_is_explicitly_rejected():
    raw = fixture("gemini").replace(b'"args":{"service":"demo"}', b'"partialArgs":[]')
    result = read_stream("gemini", [raw], lambda call: None)
    assert result.response.reason == "unsupported_stream_feature"
    assert result.response.calls == ()


def test_contract_rejection_discards_calls():
    def reject(call):
        raise ValueError("tool forbidden")
    result = read_stream("ollama", [fixture("ollama")], reject)
    assert result.response.interrupted and result.response.calls == ()


@pytest.mark.parametrize("provider", [OpenAIProvider, DeepSeekProvider, NVIDIAProvider,
                                      GeminiProvider, OllamaProvider])
def test_live_provider_capabilities_fail_explicitly(provider):
    instance = provider("fixture-model")
    assert instance.capabilities.synchronous and instance.capabilities.text
    assert instance.capabilities.context_window is None
    for feature in ("streaming", "structured_output", "context_window"):
        with pytest.raises(ProviderError, match=f"unsupported_{feature}"):
            instance.require(feature)


def test_fake_capabilities_are_explicit_too():
    provider = FakeProvider([])
    provider.require("tools")
    with pytest.raises(ProviderError, match="unsupported_streaming"):
        provider.require("streaming")
