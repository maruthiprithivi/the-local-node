"""Small, non-streaming provider boundary; no tool execution or automatic retries.

Injected transports and FakeProvider never need credentials or network access.
Live HTTP is disabled unless the caller explicitly sets allow_live=True.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
import socket
from typing import Any, Callable, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 1_048_576
MAX_CALLS = 16
MAX_ARGUMENT_BYTES = 16_384
JSON = dict[str, Any]
Transport = Callable[[str, dict[str, str], JSON, float], JSON]


class ProviderError(RuntimeError):
    """Redacted failure. Retry decisions belong to the bounded controller."""

    def __init__(self, category: str, *, retryable: bool = False,
                 status: int | None = None):
        super().__init__(f"provider failure: {category}")
        self.category = category
        self.retryable = retryable
        self.status = status


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: JSON
    metadata: JSON = field(default_factory=dict)


@dataclass(frozen=True)
class Reply:
    text: str = ""
    calls: tuple[ToolCall, ...] = ()
    usage: dict[str, int] = field(default_factory=dict)
    metadata: JSON = field(default_factory=dict)


@dataclass(frozen=True)
class Capabilities:
    synchronous: bool = True
    text: bool = True
    tools: bool = True
    streaming: bool = False
    structured_output: bool = False
    context_window: int | None = None


def _require(capabilities: Capabilities, feature: str) -> None:
    if feature not in {"synchronous", "text", "tools", "streaming", "structured_output", "context_window"}:
        raise ProviderError("unknown_capability")
    if not getattr(capabilities, feature):
        raise ProviderError(f"unsupported_{feature}")


class Provider(Protocol):
    capabilities: Capabilities
    def require(self, feature: str) -> None: ...
    def complete(self, messages: Sequence[JSON], tools: Sequence[JSON] = ()) -> Reply: ...


def assistant_message(reply: Reply) -> JSON:
    """Preserve native round-trip metadata alongside normalized conversation data."""
    message: JSON = {"role": "assistant", "content": reply.text,
                     "metadata": deepcopy(reply.metadata)}
    if reply.calls:
        message["tool_calls"] = [
            {"id": call.id, "type": "function", "function": {
                "name": call.name, "arguments": json.dumps(call.arguments)}}
            for call in reply.calls
        ]
    return message


def _encoded(value: Any, limit: int = MAX_BYTES) -> bytes:
    try:
        result = json.dumps(value, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        raise ProviderError("invalid_json") from None
    if len(result) > limit:
        raise ProviderError("size_limit")
    return result


def _arguments(value: Any) -> JSON:
    if isinstance(value, str):
        if len(value.encode("utf-8")) > MAX_ARGUMENT_BYTES:
            raise ProviderError("size_limit")
        try:
            value = json.loads(value)
        except (ValueError, RecursionError):
            raise ProviderError("malformed_arguments") from None
    if not isinstance(value, dict):
        raise ProviderError("malformed_arguments")
    _encoded(value, MAX_ARGUMENT_BYTES)
    return value


def _calls(items: Any, prefix: str, *, require_id: bool = False) -> tuple[ToolCall, ...]:
    if not isinstance(items, list) or len(items) > MAX_CALLS:
        raise ProviderError("malformed_calls" if not isinstance(items, list) else "size_limit")
    calls = []
    for index, item in enumerate(items):
        function = item["function"]
        name = function["name"]
        if require_id and (not isinstance(item.get("id"), str) or not item["id"]):
            raise ProviderError("malformed_calls")
        identifier = item.get("id") or f"{prefix}-{index}"
        if not isinstance(name, str) or not name or not isinstance(identifier, str):
            raise ProviderError("malformed_calls")
        calls.append(ToolCall(identifier, name, _arguments(function["arguments"])))
    if len({call.id for call in calls}) != len(calls):
        raise ProviderError("duplicate_call_id")
    return tuple(calls)


def _usage(raw: JSON, input_key: str, output_key: str) -> dict[str, int]:
    result = {}
    for target, source in (("input_tokens", input_key), ("output_tokens", output_key)):
        if source in raw:
            value = raw[source]
            if type(value) is not int or value < 0:
                raise ProviderError("malformed_usage")
            result[target] = value
    return result  # Missing counts remain unknown, never guessed as zero.


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Do not forward credentials to another endpoint.


def http_transport(url: str, headers: dict[str, str], payload: JSON, timeout: float) -> JSON:
    request = Request(url, data=_encoded(payload), headers=headers, method="POST")
    try:
        with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
            body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ProviderError("size_limit")
        result = json.loads(body)
    except HTTPError as error:
        category = ("authentication" if error.code in (401, 403) else
                    "rate_limit" if error.code == 429 else
                    "server" if error.code >= 500 else "request")
        raise ProviderError(category, retryable=error.code == 429 or error.code >= 500,
                            status=error.code) from None
    except (TimeoutError, socket.timeout):
        raise ProviderError("timeout", retryable=True) from None
    except URLError:
        raise ProviderError("transport", retryable=True) from None
    except (ValueError, UnicodeError, RecursionError):
        raise ProviderError("malformed_response") from None
    if not isinstance(result, dict):
        raise ProviderError("malformed_response")
    return result


class FixtureTransport:
    """Scripted wire responses, with payload capture and deliberate failure injection."""

    def __init__(self, responses: Sequence[JSON | ProviderError]):
        self.responses = iter(list(responses))
        self.requests: list[JSON] = []

    def __call__(self, url: str, headers: dict[str, str], payload: JSON, timeout: float) -> JSON:
        self.requests.append({"url": url, "payload": deepcopy(payload), "timeout": timeout})
        try:
            response = next(self.responses)
        except StopIteration:
            raise ProviderError("fixture_exhausted") from None
        if isinstance(response, ProviderError):
            raise response
        return deepcopy(response)


class FakeProvider:
    capabilities = Capabilities()

    def require(self, feature: str) -> None:
        _require(self.capabilities, feature)

    def __init__(self, replies: Sequence[Reply]):
        self.replies = iter(deepcopy(list(replies)))
        self.requests: list[JSON] = []

    def complete(self, messages: Sequence[JSON], tools: Sequence[JSON] = ()) -> Reply:
        _encoded({"messages": messages, "tools": tools})
        self.requests.append({"messages": deepcopy(list(messages)), "tools": deepcopy(list(tools))})
        try:
            reply = deepcopy(next(self.replies))
        except StopIteration:
            raise ProviderError("fixture_exhausted") from None
        if not isinstance(reply, Reply) or not isinstance(reply.text, str):
            raise ProviderError("malformed_fixture")
        if not isinstance(reply.calls, tuple) or any(not isinstance(call, ToolCall) for call in reply.calls):
            raise ProviderError("malformed_fixture")
        if not isinstance(reply.metadata, dict):
            raise ProviderError("malformed_fixture")
        for call in reply.calls:
            if (not isinstance(call.arguments, dict) or not isinstance(call.metadata, dict)
                    or not isinstance(call.id, str) or not call.id
                    or not isinstance(call.name, str) or not call.name):
                raise ProviderError("malformed_fixture")
            _arguments(call.arguments)
        _calls(assistant_message(reply).get("tool_calls", []), "fake")
        if not isinstance(reply.usage, dict) or any(type(value) is not int or value < 0
                                                   for value in reply.usage.values()):
            raise ProviderError("malformed_usage")
        _encoded({"message": assistant_message(reply), "usage": reply.usage})
        return reply


class _HTTPProvider:
    capabilities = Capabilities()

    def __init__(self, model: str, *, api_key: str = "", allow_live: bool = False,
                 transport: Transport | None = None, timeout: float = 20.0,
                 supports_tools: bool = True, max_output_tokens: int = 512,
                 endpoint: str | None = None):
        if (not isinstance(model, str) or not model or not isinstance(api_key, str)
                or type(allow_live) is not bool or type(supports_tools) is not bool
                or type(timeout) not in (int, float) or not 0 < timeout <= 60
                or type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 4096
                or (endpoint is not None and not isinstance(endpoint, str))):
            raise ProviderError("configuration")
        self.model, self.api_key = model, api_key
        self.allow_live, self.transport = allow_live, transport
        self.timeout, self.supports_tools = timeout, supports_tools
        self.capabilities = Capabilities(tools=supports_tools)
        self.max_output_tokens = max_output_tokens
        self.endpoint_override = endpoint
        self._turn = 0

    def require(self, feature: str) -> None:
        _require(self.capabilities, feature)

    def _endpoint(self) -> str:
        endpoint = self.endpoint_override or self.endpoint
        parsed = urlsplit(endpoint)
        default = urlsplit(self.endpoint)
        # Deliberately narrow teaching allowlist. Custom gateways need a reviewed extension.
        allowed_hosts = {default.hostname}
        if isinstance(self, OllamaProvider):
            allowed_hosts = {"127.0.0.1", "localhost", "::1"}
        try:
            valid_port = parsed.port
        except ValueError:
            raise ProviderError("configuration") from None
        if (parsed.hostname not in allowed_hosts or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.scheme != default.scheme
                or (not isinstance(self, OllamaProvider) and valid_port not in (None, 443))):
            raise ProviderError("untrusted_endpoint")
        return endpoint

    def _send(self, payload: JSON, tools: Sequence[JSON]) -> JSON:
        if tools and not self.supports_tools:
            raise ProviderError("unsupported_tools")
        _encoded(payload)
        if (self.transport is None or self.transport is http_transport) and not self.allow_live:
            raise ProviderError("live_disabled")
        if self.transport is None and not self.api_key and not isinstance(self, OllamaProvider):
            raise ProviderError("missing_credentials")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers.update(self.auth_headers())
        result = (self.transport or http_transport)(self._endpoint(), headers, payload, self.timeout)
        self._turn += 1
        if not isinstance(result, dict):
            raise ProviderError("malformed_response")
        _encoded(result)
        if "error" in result:
            raise ProviderError("remote_error")
        return result

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}


class _ChatProvider(_HTTPProvider):
    def complete(self, messages: Sequence[JSON], tools: Sequence[JSON] = ()) -> Reply:
        wire = []
        for message in messages:
            item = {key: deepcopy(value) for key, value in message.items() if key != "metadata"}
            # DeepSeek thinking models require their reasoning_content on follow-up turns.
            if isinstance(self, DeepSeekProvider):
                native = message.get("metadata", {}).get("reasoning_content")
                if native is not None:
                    item["reasoning_content"] = native
            wire.append(item)
        payload: JSON = {"model": self.model, "messages": wire, "stream": False}
        # OpenAI documents max_completion_tokens; these hosted APIs document max_tokens.
        token_field = "max_completion_tokens" if isinstance(self, OpenAIProvider) else "max_tokens"
        payload[token_field] = self.max_output_tokens
        if tools:
            payload["tools"] = [{"type": "function", "function": dict(tool)} for tool in tools]
        raw = self._send(payload, tools)
        try:
            choice = raw["choices"][0]
            message = choice["message"]
            text = message.get("content") or ""
            if not isinstance(text, str):
                raise ProviderError("malformed_response")
            if message.get("refusal") or choice.get("finish_reason") == "content_filter":
                raise ProviderError("refusal")
            if choice.get("finish_reason") == "length":
                raise ProviderError("truncated")
            calls = _calls(message.get("tool_calls", []), "chat", require_id=True)
            metadata = {"finish_reason": choice.get("finish_reason")}
            if "reasoning_content" in message:
                metadata["reasoning_content"] = message["reasoning_content"]
            return Reply(text, calls, _usage(raw.get("usage") or {}, "prompt_tokens", "completion_tokens"), metadata)
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("malformed_response") from None


class OpenAIProvider(_ChatProvider):
    endpoint = "https://api.openai.com/v1/chat/completions"


class DeepSeekProvider(_ChatProvider):
    endpoint = "https://api.deepseek.com/chat/completions"


class NVIDIAProvider(_ChatProvider):
    endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"
    capabilities = Capabilities(tools=False)

    def __init__(self, model: str, **kwargs):
        kwargs.setdefault("supports_tools", False)  # Verify the selected model's own docs.
        super().__init__(model, **kwargs)


class GeminiProvider(_HTTPProvider):
    @property
    def endpoint(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{quote(self.model, safe='')}:generateContent"

    def auth_headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self.api_key}

    def complete(self, messages: Sequence[JSON], tools: Sequence[JSON] = ()) -> Reply:
        contents, system = [], []
        for message in messages:
            role = message["role"]
            if role == "system":
                system.append({"text": message["content"]})
                continue
            native = message.get("metadata", {}).get("gemini_content")
            if role == "assistant" and native:
                contents.append(deepcopy(native))  # Preserve parts, ordering, thought signatures.
                continue
            parts: list[JSON] = []
            if role == "tool":
                if not message.get("name"):
                    raise ProviderError("missing_tool_name")
                response = {"result": message.get("content", "")}
                function: JSON = {"name": message["name"], "response": response}
                native_id = message.get("metadata", {}).get("gemini_function_id")
                if native_id:
                    function["id"] = native_id
                parts.append({"functionResponse": function})
            else:
                if message.get("tool_calls"):
                    raise ProviderError("missing_native_history")
                parts.append({"text": message.get("content", "")})
            contents.append({"role": "model" if role == "assistant" else "user", "parts": parts})
        payload: JSON = {"contents": contents,
                         "generationConfig": {"maxOutputTokens": self.max_output_tokens}}
        if system:
            payload["systemInstruction"] = {"parts": system}
        if tools:
            payload["tools"] = [{"functionDeclarations": list(tools)}]
        raw = self._send(payload, tools)
        try:
            if raw.get("promptFeedback", {}).get("blockReason"):
                raise ProviderError("refusal")
            candidate = raw["candidates"][0]
            reason = candidate.get("finishReason")
            if reason == "MAX_TOKENS":
                raise ProviderError("truncated")
            if reason not in (None, "STOP"):
                raise ProviderError("refusal")
            content = candidate["content"]
            text, calls = [], []
            for index, part in enumerate(content["parts"]):
                if "text" in part and not part.get("thought"):
                    if not isinstance(part["text"], str):
                        raise ProviderError("malformed_response")
                    text.append(part["text"])
                if "functionCall" in part:
                    function = part["functionCall"]
                    identifier = function.get("id") or f"gemini-{self._turn}-{index}"
                    name = function["name"]
                    if not isinstance(identifier, str) or not isinstance(name, str) or not name:
                        raise ProviderError("malformed_calls")
                    calls.append(ToolCall(identifier, name,
                                          _arguments(function.get("args", {})),
                                          {"gemini_function_id": function.get("id")}))
            if len(calls) > MAX_CALLS:
                raise ProviderError("size_limit")
            if len({call.id for call in calls}) != len(calls):
                raise ProviderError("duplicate_call_id")
            return Reply("".join(text), tuple(calls),
                         _usage(raw.get("usageMetadata", {}), "promptTokenCount", "candidatesTokenCount"),
                         {"gemini_content": deepcopy(content), "finish_reason": reason})
        except (KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("malformed_response") from None


class OllamaProvider(_HTTPProvider):
    endpoint = "http://127.0.0.1:11434/api/chat"

    def complete(self, messages: Sequence[JSON], tools: Sequence[JSON] = ()) -> Reply:
        wire = []
        for message in messages:
            native = message.get("metadata", {}).get("ollama_message")
            if message["role"] == "assistant" and native:
                wire.append(deepcopy(native))
                continue
            item = {"role": message["role"], "content": message.get("content", "")}
            if message["role"] == "tool":
                if not message.get("name"):
                    raise ProviderError("missing_tool_name")
                item["tool_name"] = message["name"]
            if message.get("tool_calls"):
                item["tool_calls"] = [{"function": {
                    "name": call["function"]["name"],
                    "arguments": _arguments(call["function"]["arguments"])}}
                    for call in message["tool_calls"]]
            wire.append(item)
        payload: JSON = {"model": self.model, "messages": wire, "stream": False,
                         "options": {"num_predict": self.max_output_tokens}}
        if tools:
            payload["tools"] = [{"type": "function", "function": dict(tool)} for tool in tools]
        raw = self._send(payload, tools)
        try:
            if raw.get("done") is not True:
                raise ProviderError("truncated")
            message = raw["message"]
            text = message.get("content", "")
            if not isinstance(text, str):
                raise ProviderError("malformed_response")
            return Reply(text, _calls(message.get("tool_calls", []), f"ollama-{self._turn}"),
                         _usage(raw, "prompt_eval_count", "eval_count"),
                         {"ollama_message": deepcopy(message), "finish_reason": raw.get("done_reason")})
        except (KeyError, TypeError, AttributeError):
            raise ProviderError("malformed_response") from None
