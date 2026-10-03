"""Bounded OFFLINE native stream decoding, followed by complete-call validation.

These readers consume supplied byte fixtures, not live HTTP. A clean native
terminal signal is required. Experimental partial Gemini function arguments,
multimodal parts and multiple candidates/choices are deliberately unsupported.
"""
from copy import deepcopy
from dataclasses import dataclass, field
import json
from typing import Callable, Iterable

from .advanced import AssembledResponse, StreamAssembler
from .providers import MAX_BYTES, MAX_CALLS, ProviderError, _arguments, _usage


@dataclass(frozen=True)
class DecodedStream:
    response: AssembledResponse
    usage: dict[str, int] = field(default_factory=dict)
    events: tuple[dict, ...] = ()
    metadata: dict = field(default_factory=dict)


def _json(text):
    def reject_constant(value):
        raise ValueError("nonfinite")
    try:
        value = json.loads(text, parse_constant=reject_constant)
    except (ValueError, RecursionError):
        raise ProviderError("malformed_stream") from None
    if not isinstance(value, dict) or "error" in value:
        raise ProviderError("malformed_stream")
    return value


def _wire_frames(chunks: Iterable[bytes], sse: bool, cancelled: Callable[[], bool]):
    """Bound raw bytes before decoding; handle arbitrary UTF-8/chunk boundaries."""
    data = bytearray()
    count = 0
    for chunk in chunks:
        if cancelled():
            raise ProviderError("cancelled")
        count += 1
        if count > 4096 or not isinstance(chunk, bytes):
            raise ProviderError("stream_input_limit")
        if len(data) + len(chunk) > MAX_BYTES:
            raise ProviderError("size_limit")
        data.extend(chunk)
    if cancelled():
        raise ProviderError("cancelled")
    try:
        text = data.decode("utf-8").replace("\r\n", "\n")
    except UnicodeError:
        raise ProviderError("malformed_stream") from None
    if sse:
        pieces = text.split("\n\n")
        if pieces[-1].strip():
            raise ProviderError("interrupted_frame")
        frames = []
        for piece in pieces[:-1]:
            lines = []
            for line in piece.split("\n"):
                if line.startswith("data:"):
                    lines.append(line[5:].removeprefix(" "))
                elif line and not line.startswith((":", "event:", "id:", "retry:")):
                    raise ProviderError("malformed_stream")
            if lines:
                frames.append("\n".join(lines))
    else:
        frames = [line for line in text.split("\n") if line.strip()]
    if len(frames) > 1024:
        raise ProviderError("stream_frame_limit")
    return frames


class _Decoder:
    def __init__(self):
        self.events = []
        self.usage = {}
        self.metadata = {}
        self.terminal = False
        self.finished = False
        self.calls = {}

    def emit(self, kind, delta=None, **identity):
        if len(self.events) >= 1023:
            raise ProviderError("stream_event_limit")
        event = {"sequence": len(self.events), "kind": kind}
        if delta is not None:
            if not isinstance(delta, str):
                raise ProviderError("malformed_stream")
            event["delta"] = delta
        event.update(identity)
        self.events.append(event)

    def full_call(self, identifier, name, arguments):
        if identifier in self.calls or len(self.calls) >= MAX_CALLS:
            raise ProviderError("duplicate_call_id" if identifier in self.calls else "size_limit")
        if not isinstance(identifier, str) or not identifier or not isinstance(name, str) or not name:
            raise ProviderError("malformed_calls")
        self.calls[identifier] = name
        self.emit("tool", json.dumps(_arguments(arguments), allow_nan=False), id=identifier, name=name)

    def chat(self, frame):
        if frame == "[DONE]":
            if self.terminal or not self.finished:
                raise ProviderError("invalid_termination")
            self.terminal = True
            return
        if self.terminal:
            raise ProviderError("data_after_termination")
        raw = _json(frame)
        if raw.get("usage") is not None:
            self.usage = _usage(raw["usage"], "prompt_tokens", "completion_tokens")
        choices = raw["choices"]
        if not choices and "usage" in raw:
            return  # Optional usage-only final chunk.
        if len(choices) != 1 or choices[0].get("index", 0) != 0 or self.finished:
            raise ProviderError("unsupported_stream_shape")
        choice = choices[0]
        delta = choice["delta"]
        if delta.get("refusal"):
            raise ProviderError("refusal")
        if delta.get("content") is not None:
            self.emit("text", delta["content"])
        for call in delta.get("tool_calls", []):
            index = call["index"]
            if type(index) is not int or not 0 <= index < MAX_CALLS:
                raise ProviderError("malformed_calls")
            pending = self.calls.setdefault(index, {"id": "", "name": "", "arguments": []})
            function = call.get("function", {})
            for key, value in (("id", call.get("id")), ("name", function.get("name"))):
                if value is not None:
                    if not isinstance(value, str):
                        raise ProviderError("malformed_calls")
                    pending[key] += value
            if "arguments" in function:
                if not isinstance(function["arguments"], str):
                    raise ProviderError("malformed_arguments")
                pending["arguments"].append(function["arguments"])
        reason = choice.get("finish_reason")
        if reason is not None:
            if reason not in ("stop", "tool_calls"):
                raise ProviderError("truncated" if reason == "length" else "refusal")
            self.finished = True
            identifiers = set()
            for pending in self.calls.values():
                identifier, name = pending["id"], pending["name"]
                if not identifier or not name or identifier in identifiers:
                    raise ProviderError("malformed_calls")
                identifiers.add(identifier)
                _arguments("".join(pending["arguments"]))
                # Buffer identity until complete; preserve argument fragment boundaries.
                for fragment in pending["arguments"]:
                    self.emit("tool", fragment, id=identifier, name=name)
                if not pending["arguments"]:
                    raise ProviderError("malformed_arguments")

    def gemini(self, frame):
        raw = _json(frame)
        if raw.get("promptFeedback", {}).get("blockReason"):
            raise ProviderError("refusal")
        if "usageMetadata" in raw:
            self.usage = _usage(raw["usageMetadata"], "promptTokenCount", "candidatesTokenCount")
        candidates = raw.get("candidates", [])
        if not candidates and "usageMetadata" in raw:
            return
        if self.terminal or len(candidates) != 1 or candidates[0].get("index", 0) != 0:
            raise ProviderError("unsupported_stream_shape")
        candidate = candidates[0]
        for part in candidate.get("content", {}).get("parts", []):
            self.metadata.setdefault("gemini_parts", []).append(deepcopy(part))
            if "text" in part and not part.get("thought"):
                self.emit("text", part["text"])
            if "functionCall" in part:
                function = part["functionCall"]
                if "partialArgs" in function or "willContinue" in function:
                    raise ProviderError("unsupported_stream_feature")
                identifier = function.get("id") or f"gemini-stream-{len(self.calls)}"
                self.full_call(identifier, function["name"], function.get("args", {}))
            if set(part) - {"text", "thought", "thoughtSignature", "functionCall", "partMetadata"}:
                raise ProviderError("unsupported_stream_feature")
        reason = candidate.get("finishReason")
        if reason is not None:
            if reason != "STOP":
                raise ProviderError("truncated" if reason == "MAX_TOKENS" else "refusal")
            self.terminal = True

    def ollama(self, frame):
        if self.terminal:
            raise ProviderError("data_after_termination")
        raw = _json(frame)
        message = raw.get("message", {})
        if message.get("content"):
            self.emit("text", message["content"])
        for call in message.get("tool_calls", []):
            function = call["function"]
            self.full_call(call.get("id") or f"ollama-stream-{len(self.calls)}",
                           function["name"], function["arguments"])
        if raw.get("done") is True:
            if raw.get("done_reason") not in (None, "stop"):
                raise ProviderError("truncated")
            self.usage = _usage(raw, "prompt_eval_count", "eval_count")
            self.terminal = True
        elif raw.get("done") is not False:
            raise ProviderError("malformed_stream")


def read_stream(provider: str, chunks: Iterable[bytes], validate: Callable[[dict], None],
                *, cancelled: Callable[[], bool] = lambda: False, output_limit=8192) -> DecodedStream:
    """Decode a complete offline fixture; publish no calls on any stream failure.

    Cancellation is cooperative at supplied chunk/frame boundaries. This function
    cannot stop a blocking iterator. Usage is optional and never guessed as zero.
    A validator checks proposals only; it must not execute tools or side effects.
    """
    if provider not in {"openai", "deepseek", "nvidia", "gemini", "ollama"}:
        raise ProviderError("unknown_provider")
    decoder = _Decoder()
    assembler = StreamAssembler(validate, limit=output_limit)
    try:
        frames = _wire_frames(chunks, provider != "ollama", cancelled)
        parser = decoder.ollama if provider == "ollama" else decoder.gemini if provider == "gemini" else decoder.chat
        for frame in frames:
            if cancelled():
                raise ProviderError("cancelled")
            parser(frame)
        if not decoder.terminal:
            raise ProviderError("interrupted_stream")
        if cancelled():
            raise ProviderError("cancelled")
        decoder.emit("end")
        for event in decoder.events:
            assembler.feed(event)
        result = assembler.finish()
        if result.interrupted:
            return DecodedStream(result)  # Discard events/usage/native metadata on failure.
        return DecodedStream(result, decoder.usage, tuple(decoder.events), decoder.metadata)
    except ProviderError as error:
        return DecodedStream(AssembledResponse("", (), True, error.category))
    except (KeyError, TypeError, IndexError, AttributeError, ValueError, OSError):
        return DecodedStream(AssembledResponse("", (), True, "malformed_stream"))
